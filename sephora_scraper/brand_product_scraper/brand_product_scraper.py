import sys
import psycopg2.extras
import psycopg2
import csv
import requests

from bs4 import BeautifulSoup
from multiprocessing.pool import ThreadPool
from pathlib import Path

from sql_statements import sql_create_product_table, sql_create_brand_table
from pydantic_basemodel import BrandInfo, ProductInfo
from db_config import host, user, password, db_name


lst_404, bad_json = [], []


def make_request(url: str) -> requests.Response | None:
    """Makes GET request and retries several times if unsuccessful.

    Args:
        url: A URL to make a get request

    Returns:
        Response | None
    """
    # proxy = 'YOUR PROXY'
    # proxies = {"https": proxy}

    headers = {
        'User-Agent': 'PostmanRuntime/7.54.0',
        'Accept-Language': 'en-MY'
    }
    num_retries = 3
    success_list = [200, 404]
    for _ in range(num_retries):
        try:
            resp = requests.get(url, headers=headers) #, proxies=proxies)
            if resp.status_code in success_list:
                return resp  # Return response if successful
        except requests.exceptions.ConnectionError:
            pass
    return None


def get_all_brand_info(resp) -> list[str]:
    """Extracts a list of all brand names from an HTML page.

    Args:
        resp: An HTML response object containing brand names

    Returns:
        list[str]: A list of all brand names found in the HTML page

    Steps:
        1. Find all HTML elements with the CSS class '.css-1d67h5w'
        2. From 'links' attribute of each element extract brand name
        4. Return the list of brand names
    """
    print('Extracting all brand names from the site...')

    list_data = resp.json()['data']
    # print(resp.json())
    brand_list = []
    for brand in list_data:
        product_base_url = f'https://www.sephora.my/api/web/v1/variants?filter%5Bbrand%5D={brand['attributes']['slug-url']}&page%5Bnumber%5D=1&page%5Bsize%5D=200'
        headers = {
            'User-Agent': 'PostmanRuntime/7.54.0',
            'Accept-Language': 'en-MY',
            'x-swa': 'web',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            }
        num_retries = 3
        success_list = [200, 404]
        for _ in range(num_retries):
            try:
                product = requests.get(product_base_url, headers=headers) #, proxies=proxies)
                if product.status_code in success_list:
                    # print(resp.json()['transformedMeta'])
                    # hold = input()
                    continue  # Return response if successful
            except requests.exceptions.ConnectionError:
                return None
        product = product.json()
        # print(product["transformedData"][0]["id"])
        product_id = []
        for product_name in product["transformedData"]:
            url = product_name["pdpUrl"]
            start = url.find('/products/') + len('/products/')
            end = url.find('/v/', start)
            product_slug = url[start:end]
            product_id.append(product_slug)
        # print(product_id)
        brand_info = BrandInfo(brand_id=brand["id"], brand_name=brand["attributes"]["slug-url"], clean_brand_name=brand["attributes"]["name"], description=brand["attributes"]["description"], total_products=len(product["transformedData"]), products=product_id)
        # print(brand_info)
        brand_list.append(brand_info.model_dump())
    # print(brand_list)
    # # Remove "/brands/" from the beginning of each link extracted with css-selector
    # brand_list = [a['href'][7:] for a in soup.select('.css-1d67h5w a[href]')]

    print(f'A total of {len(brand_list)} brand names have been collected. \nHere are the first five: {brand_list[:5]}\n')
    return brand_list


def get_product_info(url: str) -> dict | None:
    """Extracts information about a product from JSON response using the Pydantic model
    and returns validated dictionary of product information.

    Args:
        url: A URL of the product to be processed

    Returns:
        Successful response - a dictionary with processed values,
        Unsuccessful response - 'None'
    """
    resp = make_request(url)
    if resp is not None and resp.status_code == 200:
        try:
            product = ProductInfo(**resp.json()).dict()
            product_info = {**product['product_details'], **product['current_sku'], **product['categories'],
                            **product['child_count'], **product['child_max_price'], **product['child_min_price']}
            print('processing')
            return product_info
        except:
            bad_json.append(url[46:url.find('?')])
    elif resp is not None and resp.status_code == 404:
        resp = None
        lst_404.append(url[46:url.find('?')])
    return resp


def save_to_csv(all_info: list[dict], table_name: str, unique_key: str) -> None:
    """Saves the passed information to a CSV file in the 'Output' folder,
    performing an upsert based on a unique tracking column.

    Args:
        all_info: A list of dictionaries containing brand/product data.
        table_name: The name of the created csv file.
        unique_key: The string name of the primary key/unique ID column 
                    (e.g., 'brand_id' or 'product_id').
    """
    output_path = Path.cwd() / 'Output'
    output_path.mkdir(exist_ok=True)
    csv_path = output_path / f'{table_name}.csv'

    print(f'Upserting information into the "{table_name}.csv" file...')

    # 1. Read existing records into a dictionary to preserve them
    existing_records = {}
    
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as in_file:
            reader = csv.DictReader(in_file)
            for row in reader:
                # Store by unique_key (e.g., brand_id)
                # Note: CSV keys read as strings, so we match input data types
                key_value = row.get(unique_key)
                if key_value:
                    existing_records[str(key_value)] = row

    # 2. Layer incoming records on top (this handles the Upsert)
    for new_row in all_info:
        # Stringify the lookup key to safely match CSV reading behavior
        key_value = str(new_row[unique_key])
        
        # This will add new records OR completely overwrite existing ones with the new data
        existing_records[key_value] = new_row

    # 3. Write everything back out fresh
    final_rows = list(existing_records.values())
    
    if not final_rows:
        print("No data available to save.")
        return

    # Use 'w' mode to replace the file with the newly updated rows dataset
    with open(csv_path, 'w', encoding='utf-8', newline='') as out_file:
        dw = csv.DictWriter(out_file, fieldnames=list(final_rows[0].keys()))
        dw.writeheader()
        dw.writerows(final_rows)

    print(f'Information has been successfully upserted into "{table_name}.csv"\n')


def save_to_db(all_info: list[dict], create_table_statement: str, table_name: str) -> None:
    """Saves the passed information to a Postgresql database.

    Steps:
        1. Create database connection
        2. Create table in database with passed table name
        3. Insert all data in this table
        4. Сlose database connection

    Args:
        all_info: A list of dictionaries, where each dictionary contains
            information about a brand or product.
        create_table_statement: A SQL statement that creates a table in the database
        table_name: The name of the created table in the database
    """

    print(f'Saving information to the "{table_name}" table in PostgreSQL...')

    # Create connection to the database
    conn = psycopg2.connect(host=host, user=user, password=password, database=db_name)
    conn.autocommit = True

    with conn.cursor() as cursor:
        # Create table with SQL statement
        cursor.execute(create_table_statement.format(f'{table_name}'))

        # Prepare column names for `query` statement
        col_names = ','.join(list(all_info[0].keys()))  # -> 'col_n1,col_n2'
        col_names_2 = ','.join([f'%({key})s' for key in list(all_info[0].keys())])  # -> '%(col_n1)s,%(col_n2)s'

        conflict_columns = ['brand_id'] # Replace this with whatever your PRIMARY KEY column is named
        update_assignments = [f"{k} = EXCLUDED.{k}" for k in list(all_info[0].keys()) if k not in conflict_columns]
        update_string = ", ".join(update_assignments)

        # Insert data into table
        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({col_names_2}) ON CONFLICT (brand_id) DO UPDATE SET {update_string}"
        psycopg2.extras.execute_batch(cursor, query, all_info, page_size=1000)

    # Close connection to the database
    conn.close()
    print(f'Information has been successfully saved to the "{table_name}" table in PostgreSQL\n')


def main():
    # Get all brand names and put them in one list
    try:
        brand_list = get_all_brand_info(make_request('https://www.sephora.my/api/v2.6/brands?page[size]=500'))
    except Exception as e:
        sys.exit(f'An error occurred while trying to get a list of brand names: {type(e).__name__} - {e}')

    print(f'Information about {len(brand_list)} brands has been successfully extracted\n')

    # Save info about all brands to csv file and PostgreSQL
    save_to_csv(brand_list, table_name='brand_info', unique_key='brand_id')
    save_to_db(brand_list, sql_create_brand_table, table_name='brand_info')

    # # Put all product URLs in one generator
    # product_base_url = f'https://www.sephora.my/api/v2.6/products/{}?include=variants.filter_values,variants.ingredient_preference,featured_ad.virtual_bundle.bundle_elements,product_articles,filter_types&v=3w2'
    # product_urls = (product_base_url.format(prod_id)
    #                 for brand in brand_list
    #                 if brand['products'] is not None
    #                 for prod_id in brand['products'])

    # # Get inforamtion about each product
    # print('Extracting information about products...')
    # with ThreadPool(10) as pool:
    #     all_products_info = list(filter(None, pool.map(get_product_info, product_urls)))

    print(f'''Extracting product information was completed successfully.
    Details about the extraction process:
    - 404 Errors: {len(lst_404)}
      Product IDs: {lst_404}
    - Bad JSON or requiring repeated requests: {len(bad_json)}
      Product IDs: {bad_json}\n''')

    # Save info about all products to csv file and PostgreSQL
    save_to_csv(all_products_info, table_name='product_info')
    save_to_db(all_products_info, sql_create_product_table, table_name='product_info')


if __name__ == '__main__':
    main()