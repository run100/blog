import os
import re
import markdown
import shutil
from zrong.base import read_file, slog
from base import BlogError


conf = None
args = None


def _write_list(adir, rf):
    rf.write('# '+adir+'\n\n')
    is_post = adir == 'post'
    names = []
    for adir, name, fpath in self.get_mdfiles(adir):
        if is_post:
            names.append(int(name))
        else:
            names.append(name)
    if is_post:
        names = sorted(names)
    for name in names:
        _write_a_file(adir, str(name), rf)
    rf.write('\n')

def _write_a_file(adir, name, rf):
    with open(os.path.join(adir, str(name)+'.md'), 'r', encoding='utf-8') as f:
        fmt = '1. %s [%s](http://zengrong.net/%s.htm)\n'
        time = None
        title = None
        for line in f:
            if line.startswith('Title:'):
                title = line[6:].strip()
            elif line.startswith('Date:'):
                time = line[6:16]
                break
        if time and title:
            rf.write(fmt%(time, title, name))


def _write_readme():
    with open('README.md', 'w', encoding='utf-8', newline='\n') as f:
        f.write("[zrong's blog](http://zengrong.net) 中的所有文章\n")
        f.write('==========\n\n')
        f.write("----------\n\n")
        _write_list('page', f)
        _write_list('post', f)

def _rewrite_url(dirname):
    """
    Get wrong URL form articles, then convert them to a correct pattern.
    """

    url = re.compile(r'\]\(/\?p=(\d+)\)', re.S)
    for adir, name, fpath in conf.get_mdfiles(dirname):
        content = None
        fpath = os.path.join(adir, afile)
        with open(fpath, 'r', encoding='utf-8', newline='\n') as f:
            content = f.read()
            matchs = url.findall(content)
            if len(matchs) > 0:
                print(afile, matchs)
                for num in matchs:
                    content = content.replace('](/?p=%s'% num,
                            '](http://zengrong.net/post/%s.htm'%num)
            else:
                content = None
        if content:
            with open(fpath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
                print(fpath)

def _rewrite_category():
    md = markdown.Markdown(extensions=[
        'markdown.extensions.meta',
        ])
    num = 0
    for adir,name,fpath in conf.get_mdfiles('post'):
        md.convert(read_file(fpath))
        cats = [cat.strip() for cat in md.Meta['category'][0].split(',')]
        if len(cats)>1:
            print(name, cats)
            num = num + 1
    print(num)

def _write_new(name):
    try:
        dfile, dname = conf.get_new_draft(name)
    except BlogError as e:
        slog.critical(e)
        return
    shutil.copyfile(conf.get_path('templates', 'article.md'), dfile)

def build(gconf, gargs, parser=None):
    global conf
    global args
    conf = gconf
    args = gargs

    noAnyArgs = True
    if args.readme:
        _write_readme()
        noAnyArgs = False
    if args.category:
        _rewrite_category()
        noAnyArgs = False
    if args.new:
        _write_new(args.name)
        noAnyArgs = False

    if noAnyArgs and parser:
        parser.print_help()

