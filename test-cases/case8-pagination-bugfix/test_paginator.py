from paginator import paginate


def test_first_page():
    items = list(range(10))
    page = paginate(items, cursor=0, page_size=5)
    assert page.items == [0, 1, 2, 3, 4]
    assert page.next_cursor == 5


def test_second_page():
    items = list(range(10))
    page = paginate(items, cursor=5, page_size=5)
    assert page.items == [5, 6, 7, 8, 9]


def test_partial_last_page():
    items = list(range(7))
    page = paginate(items, cursor=5, page_size=5)
    assert page.items == [5, 6]
    assert page.next_cursor is None
