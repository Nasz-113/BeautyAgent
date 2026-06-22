from pickle import FALSE, TRUE
import sys
import psycopg2.extras
import psycopg2
import csv
import requests

import asyncio
import httpx

# from bs4 import BeautifulSoup
# from multiprocessing.pool import ThreadPool
from pathlib import Path

from sql_statements import sql_create_product_table, sql_create_brand_table, sql_create_filter_table, sql_create_filter_type_table, sql_create_variant_filter_table, sql_create_variant_table
from pydantic_basemodel import BrandInfo, ProductInfo, VariantInfo, VariantFilter, FilterInfo, FilterTypeInfo
from db_config import host, user, password, db_name


lst_404, bad_json = [], []


async def make_request(
        client: httpx.AsyncClient,
        url: str
) -> httpx.Response | None:

    for _ in range(3):
        try:
            resp = await client.get(url)

            if resp.status_code in [200, 404]:
                return resp

        except httpx.RequestError:
            pass

    return None


async def get_all_brand_info(client, resp) -> list[str]:
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
    # headers = {
    #     'User-Agent':
    #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    #     ' AppleWebKit/537.36 '
    #     '(KHTML, like Gecko)'
    #     ' Chrome/137.0.0.0 Safari/537.36',

    #     'Accept-Language':'en-MY,en;q=0.9',
    #     'Accept':'application/json',
    #     'Referer':'https://www.sephora.my/',
    #     'Accept-Language': 'en-MY',
    #     'x-swa': 'web',
    #     'Accept': '*/*',
    #     'Connection': 'keep-alive',
    # }
    for brand in list_data:
        product_base_url = f'https://www.sephora.my/api/web/v1/variants?filter%5Bbrand%5D={brand['attributes']['slug-url']}&page%5Bnumber%5D=1&page%5Bsize%5D=800'
        resp = await make_request(client, product_base_url)

        if resp is None:
            continue

        product = resp.json()
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


async def get_all_product_info(
        client: httpx.AsyncClient,
        brand_list: list[dict]
):

    product_list = []
    variant_list = []
    filter_list = []
    variant_filter_list = []
    filter_type_list = []

    seen_filter_ids = set()
    seen_filter_type_ids = set()
    seen_filter_type_values = set()
    seen_variant_filters = set()

    excluded_filter_ids = set()

    sem = asyncio.Semaphore(50)


    async def process_product(product_slug_url):

        async with sem:

            product_base_url = (
                f'https://www.sephora.my/api/v2.6/products/'
                f'{product_slug_url}'
                '?include=variants.filter_values,'
                'variants.ingredient_preference,'
                'featured_ad.virtual_bundle.bundle_elements,'
                'product_articles,'
                'filter_types'
            )

            resp = await make_request(
                client,
                product_base_url
            )

            if resp is None:
                return None


            product = resp.json()

            
            if product.get("errors"):
                print(f"Problematic Product: {product_slug_url}")
                return None


            return product


    tasks = []

    for brand in brand_list:
        for slug in brand["products"]:
            tasks.append(
                process_product(slug)
            )


    for coro in asyncio.as_completed(tasks):
        try:
            product = await coro
        except Exception as e:
            print(f"Task failed: {e}")
            continue

        if product is None:
            continue


        for data in product["included"]:

            # if data["id"] in [38,47,84,85] or data["id"] in ["38","47","84","85"]:
            #     print(data)
            if data["type"] == "ingredient-preferences":

                filter_type_info = FilterTypeInfo(

                    filter_type_id=data["id"],

                    value="Ingredients(Product Claim)"

                )


                if filter_type_info.value not in seen_filter_type_values:

                    filter_type_list.append(

                        filter_type_info.model_dump()

                    )

                    seen_filter_type_values.add(

                        filter_type_info.value

                    )


            elif data["type"] == "filter-types":

                filter_type_info = FilterTypeInfo(

                    filter_type_id=data["id"],

                    value=data.get(

                        "attributes",

                        {}

                    ).get(

                        "name"

                    )

                )


                if filter_type_info.filter_type_id not in seen_filter_type_ids:

                    filter_type_list.append(

                        filter_type_info.model_dump()

                    )

                    seen_filter_type_ids.add(

                        filter_type_info.filter_type_id

                    )




            elif (data["type"] == "filter-values"):

                filter_type_id = data.get("attributes", {}).get("filter-type-id")
                if filter_type_id in [38, 47, 84, 85]:
                    # Track excluded filter IDs so we skip them later
                    excluded_filter_ids.add(data["id"])
                    continue  # do NOT add to filter_list

                filter_info = FilterInfo(
                    filter_id=data["id"],
                    value=data.get("attributes", {}).get("value"),
                    filter_type_id=filter_type_id
                )
                if filter_info.filter_id not in seen_filter_ids:
                    filter_list.append(filter_info.model_dump())
                    seen_filter_ids.add(filter_info.filter_id)


            elif data["type"] == "variants":

                variant_info = VariantInfo(
                    variant_id=data["id"],
                    availability=data.get("attributes", {}).get("available", False),
                    variant_name=data["attributes"]["slug-url"],
                    clean_variant_name=data["attributes"]["name"],
                    display_original_price=data["attributes"]["display-original-price"],
                    display_price=data["attributes"]["display-price"],
                    under_sale=bool(data["attributes"]["under-sale"]),
                    product_id=product["data"]["id"]
                )
                variant_list.append(variant_info.model_dump())

                for filter_value in data["relationships"]["filter-values"]["data"]:
                    # Skip filters that belong to excluded types
                    if filter_value["id"] in excluded_filter_ids:
                        continue

                    key = (data["id"], filter_value["id"])
                    if key not in seen_variant_filters:
                        seen_variant_filters.add(key)
                        variant_filter_list.append(
                            VariantFilter(
                                variant_id=data["id"],
                                filter_id=filter_value["id"]
                            ).model_dump()
                        )



        product_info = ProductInfo(

            product_id=product["data"]["id"],

            brand_id=product["data"]["relationships"]["brand"]["data"]["id"],

            application=product["data"]["attributes"]["application"],

            product_name=product["data"]["attributes"]["slug-url"],

            clean_product_name=product["data"]["attributes"]["name"],

            description=product["data"]["attributes"]["description"],

            display_original_price=product["data"]["attributes"]["display-original-price"],

            display_price=product["data"]["attributes"]["display-price"],

            additional_benefits=product["data"]["attributes"]["benefits"]

        )


        product_list.append(

            product_info.model_dump()

        )


    return (

        product_list,

        variant_list,

        filter_list,

        variant_filter_list,

        filter_type_list

    )


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


async def main():

    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 '
        '(KHTML, like Gecko) '
        'Chrome/137.0.0.0 Safari/537.36',

        'Accept-Language': 'en-MY,en;q=0.9',
        'Accept': 'application/json',
        'Referer': 'https://www.sephora.my/',
        'x-swa': 'web',
        'Connection': 'keep-alive',
    }

    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )

    async with httpx.AsyncClient(
        headers=headers,
        timeout=30,
        limits=limits
    ) as client:

        try:

            resp = await make_request(
                client,
                'https://www.sephora.my/api/v2.6/brands?page[size]=500'
            )

            if resp is None:
                raise Exception("Unable to retrieve brands")

            brand_list = await get_all_brand_info(
                client,
                resp
            )

        except Exception as e:
            sys.exit(
                f'An error occurred while trying to get a list '
                f'of brand names: {type(e).__name__} - {e}'
            )

        print(
            f'Information about '
            f'{len(brand_list)} brands has been successfully extracted\n'
        )

        brands_to_save = []
        for brand in brand_list:
            brand_copy = brand.copy()
            brand_copy.pop("products", None)   # remove products for DB/CSV
            brands_to_save.append(brand_copy)


        save_to_csv(
            brands_to_save,
            table_name='brand_info',
            unique_key='brand_id'
        )

        save_to_db(
            brands_to_save,
            sql_create_brand_table,
            table_name='brand_info',
            conflict_columns=['brand_id']
        )


        try:

            (
                product_list,
                variant_list,
                filter_list,
                variant_filter_list,
                filter_type_list

            ) = await get_all_product_info(

                client,

                brand_list

            )


        except Exception as e:

            sys.exit(

                f'An error occurred while trying '
                f'to get product data: '

                f'{type(e).__name__} - {e}'

            )


    save_to_csv(
        product_list,
        table_name='product_info',
        unique_key='product_id'
    )

    save_to_csv(
        variant_list,
        table_name='variant_info',
        unique_key='variant_id'
    )

    save_to_csv(
        filter_list,
        table_name='filter_info',
        unique_key='filter_id'
    )

    save_to_csv(
        filter_type_list,
        table_name='filter_type_info',
        unique_key='filter_type_id'
    )


    prepared_data = []


    for vf in variant_filter_list:

        d = vf.copy()

        d['composite_id'] = (

            f"{d['variant_id']}_"

            f"{d['filter_id']}"

        )

        prepared_data.append(d)



    save_to_csv(

        prepared_data,

        table_name='variant_filter_info',

        unique_key='composite_id'

    )



    save_to_db(

        filter_type_list,

        sql_create_filter_type_table,

        table_name='filter_type_info',

        conflict_columns=['filter_type_id']

    )


    save_to_db(

        filter_list,

        sql_create_filter_table,

        table_name='filter_info',

        conflict_columns=['filter_id']

    )


    save_to_db(

        product_list,

        sql_create_product_table,

        table_name='product_info',

        conflict_columns=['product_id']

    )


    save_to_db(

        variant_list,

        sql_create_variant_table,

        table_name='variant_info',

        conflict_columns=['variant_id']

    )


    save_to_db(

        variant_filter_list,

        sql_create_variant_filter_table,

        table_name='variant_filter_info',

        conflict_columns=["variant_id", "filter_id"]

    )


if __name__ == '__main__':
    asyncio.run(main())