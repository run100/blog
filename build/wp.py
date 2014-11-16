import os
import re
import xmlrpc
import markdown
from wordpress_xmlrpc import (
        Client, WordPressPost, WordPressPage, 
        WordPressTaxonomy, WordPressTerm)
import wordpress_xmlrpc
from wordpress_xmlrpc.methods.posts import (
        GetPosts, NewPost, GetPost, EditPost)
from wordpress_xmlrpc.methods.users import GetUserInfo
from wordpress_xmlrpc.methods.options import GetOptions
from wordpress_xmlrpc.methods.taxonomies import (
        GetTaxonomies, GetTaxonomy, GetTerms, GetTerm)
from zrong.base import slog, read_file, DictBase


conf = None
args = None
wp = None

def _wpcall(method):
    global wp
    if not wp:
        wp = Client(conf.site.url, conf.site.user, conf.site.password)
    try:
        results = wp.call(method)
    except wordpress_xmlrpc.exceptions.InvalidCredentialsError as e:
        slog.error(e)
        return None
    return results

def _get_postid(as_list=False):
    if not args.query:
        return None
    if as_list:
        postids = []
        for postid in args.query:
            match = re.match(r'^(\d+)-(\d+)$', postid)
            if match:
                a = int(match.group(1))
                b = int(match.group(2))
                for i in range(a,b+1):
                    postids.append(str(i))
            else:
                postids.append(postid)
        return postids
    return args.query[0]

def _get_terms():
    if not args.query:
        slog.error('Please provide a taxonomy name! You can use '
                '"-c show -t tax" to get one.')
        return None
    termtype = args.query[0]
    if not conf[termtype]:
        results = _wpcall(GetTerms(termtype))
        if results:
            conf.save_terms(results, termtype)
    return conf[termtype]

def _print_result(result):
    if isinstance(result, WordPressTerm):
        slog.info('id=%s, group=%s, '
                'taxnomy_id=%s, name=%s, slug=%s, '
                'parent=%s, count=%d', 
                result.id, result.group, 
                result.taxonomy_id, result.name, result.slug,
                result.parent, result.count)
    elif isinstance(result, WordPressPost):
        slog.info('id=%s, date_modified=%s, '
                'slug=%s, title=%s, post_status=%s, post_type=%s', 
                result.id, str(result.date_modified), 
                result.slug, result.title,
                result.post_status, result.post_type)
    else:
        print(result)

def _print_results(results):
    if isinstance(results, list):
        for result in results:
            _print_result(result)
    else:
        _print_result(results)

def _get_article_meta(meta, post):
    adict = DictBase()
    adict.title = meta['title'][0]
    adict.slug = meta['nicename'][0]
    adict.date = meta['date'][0]
    adict.user = meta['author'][0]
    modified = meta.get('modified')
    if modified:
        adict.modified = modified[0]
    posttype = meta.get('posttype')
    if posttype:
        adict.posttype = posttype[0]
    else:
        adict.posttype = 'post'
    poststatus = meta.get('poststatus')
    if poststatus:
        adict.poststatus = poststatus[0]
    else:
        adict.poststatus = 'publish'
    return adict

def _get_article_content(afile):
    if not os.path.exists(afile):
        slog.error('The file "%s" is inexistance!'%afile)
        return None, None
    txt = read_file(afile)
    md = markdown.Markdown(extensions=[
        'markdown.extensions.meta',
        'markdown.extensions.tables',
        ])
    html = md.convert(txt)
    meta = md.Meta

    adict = DictBase()
    adict.title = meta['title'][0]
    adict.slug = meta['nicename'][0]
    adict.date = meta['date'][0]
    adict.user = meta['author'][0]
    modified = meta.get('modified')
    if modified:
        adict.modified = modified[0]
    posttype = meta.get('posttype')
    if posttype:
        adict.posttype = posttype[0]
    else:
        adict.posttype = 'post'
    poststatus = meta.get('poststatus')
    if poststatus:
        adict.poststatus = poststatus[0]
    else:
        adict.poststatus = 'publish'
    return html,adict 

def _wp_pub():
    postid = _get_postid()
    if not postid:
        slog.warning('Please provide a post id!')
        return

    if args.type != 'draft':
        return

    afile, aname = conf.get_draft(postid)
    html, meta = _get_article_content(afile)

    if meta.post_type == 'page':
        post = WordPressPage()
    else:
        post = WordPressPost()

    post.content= html
    post.title = meta.title
    post.slug = meta.nicename
    post.date = meta.date
    post.user = meta.author
    post.date_modified = meta.modified
    postid = _wpcall(NewPost(post))

    post.id = postid
    post.post_status = 'publish'
    _wpcall(EditPost(post))

    newfile, newname = conf.get_article(postid, )
    if meta.post_type == 'page':
        newfile, newname = conf.get_article(post.nicename, meta.post_type)
    else:
        newfile, newname = conf.get_article(postid, meta.post_type)

    shutil.move(afile, newfile)
    print(newfile, newname)

def _wp_update():
    postids = _get_postid(as_list=True)
    if not postids:
        slog.warning('Please provide a post id!')
        return

    if not conf.is_article(args.type):
        return

    def _update_a_post(postid):
        afile, aname = conf.get_article(postid, args.type)
        html, meta = _get_article_content(afile)
        resultclass = WordPressPost
        if args.type == 'page':
            postid = meta.postid
            resultclass = WordPressPage
        elif args.type == 'draft':
            postid = meta.postid
            if meta.post_type == 'page':
                resultclass = WordPressPage

        post = _wpcall(GetPost(postid, result_class=resultclass))
        if not post:
            return
        _print_results(post)
        post.title = meta.title
        post.slug = meta.nicename
        post.content = html
        if meta.modified:
            post.date_modified = meta.modified
        post.post_status = 'publish'

        succ = _wpcall(EditPost(postid, post))
        if succ == None:
            return
        if succ:
            slog.info('Update %s successfully!'%postid)
        else:
            slog.info('Update %s fail!'%postid)

    for postid in postids:
        _update_a_post(postid)

def _wp_del():
    pass

def _wp_show():
    method = None
    if args.type == 'post' or args.type == 'page':

        field = {'post_type':'page'} \
            if args.type == 'page' else {}
        field['number'] = args.number
        field['orderby'] = args.orderby
        field['order'] = args.order

        resultclass = WordPressPage \
            if args.type == 'page' else WordPressPost

        if args.query:
            method = GetPost(_get_postid(), result_class=resultclass)
        else:
            method = GetPosts(field, result_class=resultclass)

    elif args.type == 'draft':
        for adir, aname, afile in conf.get_mdfiles('draft'):
            slog.info(afile)
    elif args.type == 'option':
        method = GetOptions([])
    elif args.type == 'tax':
        method = GetTaxonomies()
    elif args.type == 'term':
        terms = _get_terms()
        if terms:
            _print_results(terms)

    if not method:
        return

    results = _wpcall(method)
    if not results:
        return

    _print_results(results)

def build(gconf, gargs, parser=None):
    global conf
    global args
    conf = gconf
    args = gargs

    noAnyArgs = True
    if args.user:
        conf.site.user = args.user
    if args.password:
        conf.site.password = args.password
    if args.site:
        if args.site.rfind('xmlrpc.php')>0:
            conf.site.url = args.site
        else:
            removeslash = args.site.rfind('/')
            if removeslash == len(args.site)-1:
                removeslash = args.site[0:removeslash]
            else:
                removeslash = args.site
            conf.site.url = '%s/xmlrpc.php'%removeslash
    if args.action:
        eval('_wp_'+args.action)()
        noAnyArgs = False

    if noAnyArgs and parser:
        parser.print_help()

