sql_create_reviews_table = """
CREATE TABLE IF NOT EXISTS {}(
    review_id int PRIMARY KEY,
    submission_time timestamptz,
    product_id int references product_info(product_id),
    variant_id int references variant_info(variant_id),
    reviewed_from text,
    rating int,
    title text,
    review_text text,
    user_nickname text
    );
"""
