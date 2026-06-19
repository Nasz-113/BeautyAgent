from pickle import FALSE, TRUE
import sys
import psycopg2.extras
import psycopg2
import csv
import requests

# from bs4 import BeautifulSoup
# from multiprocessing.pool import ThreadPool
from pathlib import Path

from sql_statements import sql_create_product_table, sql_create_brand_table, sql_create_filter_table, sql_create_filter_type_table, sql_create_variant_filter_table, sql_create_variant_table
from pydantic_basemodel import BrandInfo, ProductInfo, VariantInfo, VariantFilter, FilterInfo, FilterTypeInfo
from db_config import host, user, password, db_name


lst_404, bad_json = [], []


def make_request(url: str, headers: dict) -> requests.Response | None:
    """Makes GET request and retries several times if unsuccessful.

    Args:
        url: A URL to make a get request

    Returns:
        Response | None
    """
    # proxy = 'YOUR PROXY'
    # proxies = {"https": proxy}

    # headers = {
    #     'User-Agent': 'PostmanRuntime/7.54.0',
    #     'Accept-Language': 'en-MY'
    # }
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
    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ' AppleWebKit/537.36 '
        '(KHTML, like Gecko)'
        ' Chrome/137.0.0.0 Safari/537.36',

        'Accept-Language':'en-MY,en;q=0.9',
        'Accept':'application/json',
        'Referer':'https://www.sephora.my/',
        'Accept-Language': 'en-MY',
        'x-swa': 'web',
        'Accept': '*/*',
        'Connection': 'keep-alive',
    }
    for brand in list_data:
        product_base_url = f'https://www.sephora.my/api/web/v1/variants?filter%5Bbrand%5D={brand['attributes']['slug-url']}&page%5Bnumber%5D=1&page%5Bsize%5D=800'
        product = make_request(product_base_url,headers).json()
        # print(product["transformedData"][0]["id"])
        product_name = []
        for product_data in product["transformedData"]:
            url = product_data["pdpUrl"]
            start = url.find('/products/') + len('/products/')
            end = url.find('/v/', start)
            product_slug = url[start:end]
            product_name.append(product_slug)
        # print(product_id)
        brand_info = BrandInfo(brand_id=brand["id"], brand_name=brand["attributes"]["slug-url"], clean_brand_name=brand["attributes"]["name"], description=brand["attributes"]["description"], total_products=len(product["transformedData"]), products=product_name)
        # print(brand_info)
        brand_list.append(brand_info.model_dump())
    # print(brand_list)
    # # Remove "/brands/" from the beginning of each link extracted with css-selector
    # brand_list = [a['href'][7:] for a in soup.select('.css-1d67h5w a[href]')]

    print(f'A total of {len(brand_list)} brand names have been collected. \nHere are the first five: {brand_list[:5]}\n')
    return brand_list


def get_all_product_info(headers: dict, brand_list: list[dict]):
    """Extracts information about a product from JSON response using the Pydantic model
    and returns validated dictionary of product information.

    Args:
        url: A URL of the product to be processed

    Returns:
        Successful response - a dictionary with processed values,
        Unsuccessful response - 'None'
    """
    product_list, variant_list, filter_list, variant_filter_list, filter_type_list = [], [], [], [], []
    for brand in brand_list:
        for product_slug_url in brand["products"]:
            product_base_url = f'https://www.sephora.my/api/v2.6/products/{product_slug_url}?include=variants.filter_values,variants.ingredient_preference,featured_ad.virtual_bundle.bundle_elements,product_articles,filter_types'
            product = make_request(product_base_url,headers).json()
            if product.get("errors"):
                print(f"Problematic Product: {product_slug_url}")
                continue
            # print(f"Good to extract data: {product_slug_url}")
            for data in product["included"]:
                if data["id"] in [38, 47, 84, 85]:
                        print(data)
                if data["type"] == "ingredient-preferences":
                    filter_type_info = FilterTypeInfo(
                        filter_type_id = data["id"], 
                        value = "Ingredients(Product Claim)"
                        )
                    if filter_type_info.value not in [x["value"] for x in filter_type_list]:
                        filter_type_list.append(filter_type_info.model_dump())
                elif (data["type"] == "filter-types"):
                    filter_type_info = FilterTypeInfo(
                        filter_type_id = data["id"], 
                        value = data.get("attributes", {}).get("name")
                        )
                    if filter_type_info.filter_type_id not in [x["filter_type_id"] for x in filter_type_list]:
                        filter_type_list.append(filter_type_info.model_dump())
                elif data["type"] == "filter-values" and data.get("attributes", {}).get("filter-type-id") not in [38, 47, 84, 85]:
                    filter_info = FilterInfo(
                        filter_id = data["id"], 
                        value = data.get("attributes", {}).get("value"), 
                        filter_type_id = data.get("attributes", {}).get("filter-type-id")
                        )
                    if filter_info.filter_id not in [x["filter_id"] for x in filter_list]:
                        filter_list.append(filter_info.model_dump())
                elif data["type"] == "variants":
                    variant_info = VariantInfo(
                        variant_id = data["id"], 
                        availability = data.get("attributes", {}).get("available", False),
                        variant_name = data["attributes"]["slug-url"],
                        clean_variant_name = data["attributes"]["name"],
                        display_original_price = data["attributes"]["display-original-price"],
                        display_price = data["attributes"]["display-price"],
                        under_sale = bool(data["attributes"]["under-sale"])
                        )
                    variant_list.append(variant_info.model_dump())
                    for filter_value in data["relationships"]["filter-values"]["data"]:
                        variant_filter_list.append(VariantFilter(variant_id= data["id"], filter_id = filter_value["id"]).model_dump())
                else:
                    continue
            
            product_info = ProductInfo(
                    product_id = product["data"]["id"],
                    brand_id = product["data"]["relationships"]["brand"]["data"]["id"],
                    application = product["data"]["attributes"]["application"],
                    product_name = product["data"]["attributes"]["slug-url"],
                    clean_product_name = product["data"]["attributes"]["name"],
                    description = product["data"]["attributes"]["description"],
                    display_original_price = product["data"]["attributes"]["display-original-price"],
                    display_price = product["data"]["attributes"]["display-price"],
                    additional_benefits = product["data"]["attributes"]["benefits"]
            )    
            # print(brand_info)
            product_list.append(product_info.model_dump())

    return product_list, variant_list, filter_list, variant_filter_list, filter_type_list


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


def save_to_db(all_info: list[dict], create_table_statement: str, table_name: str, conflict_columns: list[str]) -> None:
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

        conflict_string = ", ".join(conflict_columns)
        update_assignments = [f"{k} = EXCLUDED.{k}" for k in list(all_info[0].keys()) if k not in conflict_columns]
        update_string = ", ".join(update_assignments)

        # Insert data into table
        if update_assignments:
            query = f"""
            INSERT INTO {table_name} ({col_names})
            VALUES ({col_names_2})
            ON CONFLICT ({conflict_string})
            DO UPDATE SET {update_string}
            """
        else:
            query = f"""
            INSERT INTO {table_name} ({col_names})
            VALUES ({col_names_2})
            ON CONFLICT ({conflict_string})
            DO NOTHING
            """
        psycopg2.extras.execute_batch(cursor, query, all_info, page_size=1000)

    # Close connection to the database
    conn.close()
    print(f'Information has been successfully saved to the "{table_name}" table in PostgreSQL\n')


def main():
    # Get all brand names and put them in one list
    try:
        headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ' AppleWebKit/537.36 '
        '(KHTML, like Gecko)'
        ' Chrome/137.0.0.0 Safari/537.36',

        'Accept-Language':'en-MY,en;q=0.9',
        'Accept':'application/json',
        'Referer':'https://www.sephora.my/',
        'Accept-Language': 'en-MY',
        'x-swa': 'web',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        }
        brand_list = get_all_brand_info(make_request('https://www.sephora.my/api/v2.6/brands?page[size]=500', headers))
    except Exception as e:
        sys.exit(f'An error occurred while trying to get a list of brand names: {type(e).__name__} - {e}')

    print(f'Information about {len(brand_list)} brands has been successfully extracted\n')

    # Save info about all brands to csv file and PostgreSQL
    for brand in brand_list:
        # 1. Pop 'products' out of the individual brand dictionary safely
        product_list_temp = brand.pop("products", [])
        
        # 2. Save the individual brand (wrapped in a list so your functions still work)
        save_to_csv([brand], table_name='brand_info', unique_key='brand_id')
        save_to_db([brand], sql_create_brand_table, table_name='brand_info', conflict_columns=["brand_id"])
        
        # 3. Put 'products' back into the brand dictionary
        brand["products"] = product_list_temp

    # Put all product URLs in one generator
    try:
        headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ' AppleWebKit/537.36 '
        '(KHTML, like Gecko)'
        ' Chrome/137.0.0.0 Safari/537.36',

        'Accept-Language':'en-MY,en;q=0.9',
        'Accept':'application/json',
        'Referer':'https://www.sephora.my/',
        'Accept-Language': 'en-MY',
        'x-swa': 'web',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        }
        product_list, variant_list, filter_list, variant_filter_list, filter_type_list = get_all_product_info(headers, brand_list)
    except Exception as e:
        print(e)
        sys.exit(f'An error occurred while trying to get a list of product names: {type(e).__name__} - {e}')

    save_to_csv(product_list, table_name='product_info', unique_key='product_id')
    save_to_csv(variant_list, table_name='variant_info', unique_key='variant_id')
    save_to_csv(filter_list, table_name='filter_info', unique_key='filter_id')
    save_to_csv(filter_type_list, table_name='filter_type_info', unique_key='filter_type_id')

    prepared_data = []
    for vf in variant_filter_list:
        data_dict = vf
        
        # Create a unique string identifier for the upsert logic to use
        data_dict['composite_id'] = f"{data_dict['variant_id']}_{data_dict['filter_id']}"
        
        prepared_data.append(data_dict)
    save_to_csv(prepared_data, table_name='variant_filter_info', unique_key='composite_id')

    save_to_db(filter_type_list, sql_create_filter_type_table, table_name='filter_type_info', conflict_columns=["filter_type_id"])
    save_to_db(filter_list, sql_create_filter_table, table_name='filter_info', conflict_columns=["filter_id"])
    save_to_db(product_list, sql_create_product_table, table_name='product_info', conflict_columns=["product_id"])
    save_to_db(variant_list, sql_create_variant_table, table_name='variant_info', conflict_columns=["variant_id"])
    save_to_db(variant_filter_list, sql_create_variant_filter_table, table_name='variant_filter_info', conflict_columns=[])
    # product_urls = (product_base_url.format(prod_id)
    #                 for brand in brand_list
    #                 if brand['products'] is not None
    #                 for prod_id in brand['products'])

    # # Get inforamtion about each product
    # print('Extracting information about products...')
    # with ThreadPool(10) as pool:
    #     all_products_info = list(filter(None, pool.map(get_product_info, product_urls)))

    # print(f'''Extracting product information was completed successfully.
    # Details about the extraction process:
    # - 404 Errors: {len(lst_404)}
    #   Product IDs: {lst_404}
    # - Bad JSON or requiring repeated requests: {len(bad_json)}
    #   Product IDs: {bad_json}\n''')

    # # Save info about all products to csv file and PostgreSQL
    # save_to_csv(all_products_info, table_name='product_info')
    # save_to_db(all_products_info, sql_create_product_table, table_name='product_info')


if __name__ == '__main__':
    main()