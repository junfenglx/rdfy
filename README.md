###content
[toc]

### rdfy
a tool for download ren da fu yin zi liao

#### Setup
First
cp
./nips15submit_e.sty
./my_arch_ctex_fonts.sty
to your [TEXMFHOME|TEXMFLOCAL]/tex/latex/ directory

Then install Requirements.

You should have authorization to browse the papers on rendafuyin website.

#### Usage
> usage: rdfy.py [-h] [--slow] --dh P_ID --nf YEAR [--version]
> 
> rdfy download tool
> 
> optional arguments:
>   -h, --help          show this help message and exit
>   --slow              slow download speed
>   --dh P_ID           the periodical ID
>   --nf YEAR, -Y YEAR  the year want to download
>   --version, -v       show program's version number and exit

#### Requirements
1. Python
2. Requests
3. texlive
4. some Chinese fonts used in ./my_arch_ctex_fonts.sty


#### References
[setup texlive chinese ctex on linux][1]

[1]: http://www.cnblogs.com/lienhua34/p/3675027.html
