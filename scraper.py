import re
from urllib.parse import urlparse, urldefrag, parse_qs, urljoin
from urllib import robotparser
from bs4 import BeautifulSoup

stopwords = ["a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as",
             "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
             "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
             "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
             "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
             "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
             "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of",
             "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
             "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
             "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
             "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
             "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
             "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's",
             "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
             "yourself", "yourselves"]

url_cache = set()   #used to store all the unique web pages extracted
largest_page_wordcount = 0
largest_page_url = ""
ics_subdomains = {}
unique_words = {}
unique_url_pages = 0


def scraper(url, resp):
    finallist = []
    links = extract_next_links(url, resp)
    if resp.status != 200:  #return an empty list if web page not succesfully opened.
        return []
    else:
        for i in links:
            if is_valid(i):
                finallist.append(i) 
                subdomain_count(i)  #function call to determine the subdomain and its count {deliverable requirement}
        get_report(url, resp)   #function call to determine the unique urls, longest page, common words and its count {deliverable requirement}
    return finallist


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = list()
    if resp.status != 200:
        return links
    soup = BeautifulSoup(resp.raw_response.content, "html.parser") #using Beautifulsoup library to parse the content of the webpage.
    word_count = len(soup.get_text().split())   #list of all content words in the webpage 
    length = len(str(soup))     #size of the webpage.

    if length < 10 * 1024 * 1024 and word_count > 300: #to check for large files and low information page

        for a in soup.find_all('a'):    #parses all links from the webpage
            link = a.get("href")
            if link:
                absolute_link = urljoin(url, link)  #converts all links to absolute urls
                if absolute_link.startswith("https") or absolute_link.startswith("http"):
                    defragged_link = urldefrag(absolute_link).url   #defrags the urls
                    links.append(defragged_link)
                else:
                    continue

    
    return links
    


def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    #Citation - "https://support.archive-it.org/hc/en-us/articles/208332963-How-to-modify-your-crawl-scope-with-a-Regular-Expression", "https://docs.python.org/3/library/urllib.robotparser.html"
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpe?g|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False

        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        #check for only valid domains
        domaincheck = True
        if (domain.endswith(".ics.uci.edu") or
            domain.endswith(".cs.uci.edu") or
            domain.endswith(".informatics.uci.edu") or
                domain.endswith(".stat.uci.edu")):
            domaincheck = True
        else:
            domaincheck = False
        if domaincheck == False:
            return False

        # robots.txt check
        rp = robotparser.RobotFileParser()
        rp.set_url(f'https://{domain}/robots.txt')
        rp.read()
        if not rp.can_fetch('*', url):
            #print(f'The URL "{url}" is NOT ALLOWED for crawlling.')
            return False
        # event/events check
        if "/event" in path or "/events" in path:
            return False

        # calendar check - {put website from where we got regex}
        if re.match(r"^.calendar.$", url):
            return False

        # checks for lond/repeating directories
        if re.match("^.?(/.+?/).?\1.$|^.?/(.+?/)\2.*$", path):
            return False

        # long webpages with low information value
        reject = ['doku.php', 'ical', '.jpg', 'pdf',
                  '/pdf/', 'ical', 'mailto', '?share=', '?format', 'archive']
        for j in reject:
            if j in url:
                return False

        # Extra pathways check
        if url.count('/') > 5:
            return False

        # Extra queries check
        if len(parse_qs(urlparse(url).query)) > 5:
            return False

        # already in url_cache check
        if url in url_cache:
            # print("Too many same urlssss")
            return False

        # else add in the url_cache 
        url_cache.add(url)
        return True
    except TypeError:
        print("TypeError for ", parsed)
        return False


def subdomain_count(url):
    '''subdomain dictionary making - counts the number of subdomains under '.ics.uci.edu' into a dict ics_subdomains<string, int>'''

    domain = urlparse(url).netloc.lower()  # domain of the url
    if not (domain.endswith(".ics.uci.edu")):
        pass
    else:
        sub = domain[:domain.index(".ics.uci.edu")]
        if sub in ics_subdomains:
            if url in ics_subdomains[sub]:
                pass
            else:
                ics_subdomains[sub].append(url)
        else:
            ics_subdomains[sub] = []
            ics_subdomains[sub].append(url)


def get_report(url, resp):
    global largest_page_url, largest_page_wordcount, ics_subdomains, unique_url_pages
    soup = BeautifulSoup(resp.raw_response.content,
                         "html.parser")  # content of the page

    page_text = soup.get_text()  # text of the content page
    # list of all words on the page
    words_tokenized = re.findall(r'[a-zA-Z0-9]+', page_text)
    parsed = urlparse(url)  # url formatted
    domain = parsed.netloc.lower()  # domain of the url

    # common word count
    for i in words_tokenized:
        if i in stopwords or len(i)<=3:
            continue
        elif i in unique_words:
            unique_words[i] += 1
        else:
            unique_words[i] = 1

    # longest page
    page_word_count = len(words_tokenized)
    if page_word_count > largest_page_wordcount:
        largest_page_wordcount = page_word_count
        largest_page_url = url

    # number of unique pages
    unique_url_pages = len(url_cache)  # 1st deliverable report


def write_report():
    '''Creates a Report.txt file to write all the stats of the crawler.'''
    global largest_page_url, largest_page_wordcount, ics_subdomains, unique_url_pages, unique_words
    ics_subdomains = dict(sorted(ics_subdomains.items()))   #sorts the dict as per requiremen
    filename = "Report.txt"
    tfreq = sorted(unique_words.items(), key=lambda x: (-x[1], x[0])) #sorts the list as per requirement
    with open(filename, 'w') as file:
        file.write(
            f"Largest page word count and url is: {largest_page_url} -> {largest_page_wordcount}\n")
        file.write(
            f"count of number of pages scraped by scraper -> {unique_url_pages}\n")
        for i in ics_subdomains:
            file.write(f"http://{i}.ics.uci.edu -> {len(ics_subdomains[i])}\n")
        counter = 0
        for i, j in tfreq:
            if counter == 50:
                break
            file.write(f"{i} -> {j}\n")
            counter += 1
