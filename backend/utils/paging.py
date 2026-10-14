MAX_PAGE = 10000


# Read a positive whole number from a query string value, or use the
# fallback when it is missing, not a number, or below 1.
def read_positive_int(raw_value, fallback):
    try:
        number = int(raw_value)
    except (TypeError, ValueError):
        return fallback
    if number < 1:
        return fallback
    return number


# Read ?page= and ?page_size= from the request, with safe limits.
# The page size is capped so nobody can ask for the whole collection in one
# call. Returns (page, page_size, skip) ready for a MongoDB query.
def read_paging(args, default_size=20, max_size=100):
    page = read_positive_int(args.get("page"), 1)
    page_size = read_positive_int(args.get("page_size"), default_size)
    if page > MAX_PAGE:
        page = MAX_PAGE
    if page_size > max_size:
        page_size = max_size
    return page, page_size, (page - 1) * page_size
