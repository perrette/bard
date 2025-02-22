import requests
from bs4 import BeautifulSoup
from readability import Document


# Function to remove tags
def remove_tags(html):
    """https://www.geeksforgeeks.org/remove-all-style-scripts-and-html-tags-using-beautifulsoup/
    """
    # parse html content
    soup = BeautifulSoup(html, "html.parser")

    for data in soup(['style', 'script']):
        # Remove tags
        data.decompose()

    # return data by retrieving the tag content
    return ' '.join(soup.stripped_strings)


def extract_readable_html(html):
    doc = Document(html)
    return "\n".join([doc.title(), doc.summary()])


def extract_text_from_html(html):
    simple_html = extract_readable_html(html)
    return remove_tags(simple_html)


def extract_text_from_url(url):
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        url = "https://" + url
        response = requests.get(url)
    return extract_text_from_html(response.content)