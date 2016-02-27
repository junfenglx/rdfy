#!/usr/bin/env python
# encoding: utf-8

import os
import os.path
import logging
import subprocess
import time
import re
import argparse

import requests
import bs4
from tornado import template
from tornado.escape import to_basestring

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.INFO
)

HEADERS = dict()
HEADERS["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"
BASE_OUT = "./output"

CONV = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\^{}',
    '\\': r'\textbackslash{}',
    # '<': r'\textless',
    # '>': r'\textgreater',
}
REGEX = re.compile('|'.join(re.escape(key) for key in sorted(CONV.keys(), key=lambda item: - len(item))))


def tex_escape(text):
    return REGEX.sub(lambda match: CONV[match.group()], to_basestring(text))


class Article(object):
    def __init__(self, id_, bt, tt, zz, au, nf, qh):
        self.id_ = id_
        self.bt = bt
        self.tt = tt
        self.zz = zz
        self.au = au
        self.nf = nf
        self.qh = qh
        self.til = None
        self.stil = None
        self.aut = None
        self.aino = None
        self.ast = None
        self.text = None

    def __str__(self):
        return "ID: {id_}\nBT: {bt}\nTT: {tt}\nZZ: {zz}\nAU: {au}\nNF: {nf}\nQH: {qh}".format(
            id_=self.id_, bt=self.bt, tt=self.tt, zz=self.zz,
            au=self.au, nf=self.nf, qh=self.qh
        )

    def set_base_info(self, soup):
        r1 = soup.find("R1")
        self.til = r1.find("til").text
        stil = r1.find("stil").text
        if not stil:
            stil = r1.find("etil").text
        self.stil = stil
        self.aut = r1.find("aut").text
        self.aino = r1.find("aino").text
        self.ast = r1.find("ast").text


class RDFY(object):
    ARTICLE_LIST_URL = "http://ipub.exuezhe.com/Qk/GetArtList?dh={dh}&nf={nf}&qh={qh}&ps=24&pn=1"
    ARTICLE_TEXT_URL = "http://ipub.exuezhe.com/Qw/GetTextArt?id={id_}&pn=1&ps=100&kw="
    ARTICLE_BASE_URL = "http://ipub.exuezhe.com/Qw/GetBaseArt?id={id_}&kw="

    def __init__(self, dh, nf, slow):
        self.session = requests.Session()
        self.session.headers = HEADERS
        self.dh = dh
        self.nf = nf
        self.slow = slow
        namespace = dict(tex_escape=tex_escape)
        loader = template.Loader('.', autoescape="tex_escape", namespace=namespace)
        self.template = loader.load("rdfy_template.tex")
        self.tex_dir = os.path.join(BASE_OUT, "tex", self.dh, self.nf)
        if not os.path.isdir(self.tex_dir):
            os.makedirs(self.tex_dir)
        self.pdf_dir = os.path.join(BASE_OUT, "pdf", self.dh, self.nf)
        if not os.path.isdir(self.pdf_dir):
            os.makedirs(self.pdf_dir)
        self.failed = []

    def get_article_list(self, qh):
        qh_tex_dir = os.path.join(self.tex_dir, qh)
        qh_pdf_dir = os.path.join(self.pdf_dir, qh)
        if not os.path.isdir(qh_tex_dir):
            os.mkdir(qh_tex_dir)
        if not os.path.isdir(qh_pdf_dir):
            os.mkdir(qh_pdf_dir)

        url = self.ARTICLE_LIST_URL.format(dh=self.dh,
                                           nf=self.nf,
                                           qh=qh)
        r = self.session.get(url)
        soup = bs4.BeautifulSoup(r.content, "xml")
        r1_list = soup.find_all("R1")
        r2 = int(soup.find("R2").text)
        logging.warning("R2: %s", r2)
        logging.warning("in get_article_list len(r1_list) == r2: %s", len(r1_list)==r2)
        articles = []
        qh_tex_dir = os.path.join(self.tex_dir, qh)
        for r1 in r1_list:
            id_ = r1.find("ID").text
            bt = r1.find("BT").text
            tt = r1.find("TT").text.strip().replace("/", "-")
            zz = r1.find("ZZ").text
            au = r1.find("AU").text.strip().replace("/", "-")

            filename = tt + "-" + au + ".tex"
            filename = os.path.join(qh_tex_dir, filename)
            if os.path.isfile(filename):
                continue

            nf = r1.find("NF").text
            qh = r1.find("QH").text
            article = Article(id_, bt, tt, zz, au, nf, qh)
            logging.debug(article)
            articles.append(article)

        return articles

    def get_article_base(self, article):
        url = self.ARTICLE_BASE_URL.format(id_=article.id_)
        r = self.session.get(url)
        soup = bs4.BeautifulSoup(r.content, "xml")
        article.set_base_info(soup)

    def get_article_text(self, article):
        url = self.ARTICLE_TEXT_URL.format(id_=article.id_)
        r = self.session.get(url)
        soup = bs4.BeautifulSoup(r.content, "xml")
        r1_list = soup.find_all("R1")
        r2 = int(soup.find("R2").text)
        logging.warning("in get_article_text len(r1_list) == r2: %s", len(r1_list)==r2)
        text = []
        for r1 in r1_list:
            ctt = r1.find("ctt").text
            ctt = ctt.replace("</p>", "\n\n")
            text.append(ctt)

        text = ''.join(text)
        logging.debug(text)
        article.text = text

    def _gen_tex_article(self, article):
        logging.debug("type: %s", type(article.text))
        art_tex = self.template.generate(article=article)
        logging.debug(art_tex)
        return art_tex

    def save_tex_article(self, article, qh):
        art_tex = self._gen_tex_article(article)

        filename = article.tt + "-" + article.au + ".tex"
        qh_tex_dir = os.path.join(self.tex_dir, qh)
        filename = os.path.join(qh_tex_dir, filename)

        with open(filename, "wb") as f:
            f.write(art_tex)
        return filename

    def save_pdf_article(self, article, qh):
        tex_file = self.save_tex_article(article, qh)
        qh_pdf_dir = os.path.join(self.pdf_dir, qh)
        cmd = ["xelatex", "-output-directory=" + qh_pdf_dir, "-interaction=batchmode", tex_file]
        ret = subprocess.call(cmd)
        logging.info("cmd: %s return code %s", ' '.join(cmd), ret)
        if ret != 0:
            self.failed.append(article)
            # roll back, remove tex_file
            os.rename(tex_file, tex_file + ".error")

    def run(self):
        for qh in range(1, 13):
            qh = "{qh:02d}".format(qh=qh)
            logging.info("process qh=%s", qh)
            articles = self.get_article_list(qh)
            for article in articles:
                logging.info("download article: %s", article)
                self.get_article_base(article)
                self.get_article_text(article)
                self.save_pdf_article(article, qh)
                if self.slow:
                    time.sleep(1)
            if self.slow:
                time.sleep(5)


if __name__ == "__main__":
    dh = "J4"
    nf = "2015"
    slow = False
    parser = argparse.ArgumentParser(description="rdfy download tool")
    parser.add_argument("--slow", action='store_true', default=False, help="slow download speed")
    parser.add_argument("--dh", required=True, help="the periodical ID", metavar="P_ID")
    parser.add_argument("--nf", "-Y", required=True, help="the year want to download", metavar="YEAR")
    parser.add_argument('--version', "-v", action='version', version='%(prog)s 0.01')
    args = parser.parse_args()
    logging.info(args)

    rdfy = RDFY(dh=args.dh, nf=args.nf, slow=args.slow)
    """
    articles = rdfy.get_article_list("01")
    rdfy.get_article_base(articles[0])
    rdfy.get_article_text(articles[0])
    rdfy.save_pdf_article(articles[0], "01")
    """
    rdfy.run()
    logging.info("%s failed downloaded articles", len(rdfy.failed))
    for article in rdfy.failed:
        logging.info(article)
