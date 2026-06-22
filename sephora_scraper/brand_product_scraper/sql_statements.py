sql_create_product_table = """
CREATE TABLE IF NOT EXISTS {}(
    product_id int PRIMARY KEY,
    brand_id int REFERENCES brand_info(brand_id),
    application text,
    product_name text,
    clean_product_name text,
    description text,
    display_original_price text,
    display_price text,
    additional_benefits text);
"""

sql_create_variant_table = """
CREATE TABLE IF NOT EXISTS {}(
    variant_id int PRIMARY KEY,
    availability boolean default true,
    variant_name text,
    clean_variant_name text,
    display_original_price text,
    display_price text,
    under_sale boolean default true,
    product_id int references product_info(product_id));
"""

sql_create_filter_type_table = """
CREATE TABLE IF NOT EXISTS {}(
    filter_type_id int PRIMARY KEY,
    value text);
"""

sql_create_filter_table = """
CREATE TABLE IF NOT EXISTS {}(
    filter_id int PRIMARY KEY,
    value text,
    filter_type_id int references filter_type_info(filter_type_id));
"""

sql_create_variant_filter_table = """
CREATE TABLE IF NOT EXISTS {}(
    variant_id int,
    filter_id int,
    PRIMARY KEY (variant_id, filter_id),
    FOREIGN KEY (variant_id)
        REFERENCES variant_info(variant_id),
    FOREIGN KEY (filter_id)
        REFERENCES filter_info(filter_id)
);
"""

sql_create_brand_table = """
CREATE TABLE IF NOT EXISTS {}(
    brand_id int PRIMARY KEY,
    brand_name text,
    clean_brand_name text,
    description text,
    total_products int);
"""