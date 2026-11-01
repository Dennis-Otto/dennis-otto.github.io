"""The code of the hooks of this website and of its script, a module for each
concern, with nothing but the standard library. .github/mkdocs_project.py is what MkDocs
loads and what the scripts and the workflows run; it puts its own folder on sys.path,
where it finds this package. A module imports only those above it in this list, so the
list is also the order in which to read them:

    catalog       the data classes of projects.toml and the words that they share
    web           how the hooks ask the web: a download, a status, a file
    reader        reads projects.toml and names everything wrong with it at once
    render        the cards of the home pages, the Trust page and the README tables
    search        the search index of every project website in the search of this one
    releases      the Releases page and What's new, from the API of GitHub
    requirements  what a project works with, from a file of its repository
    address       the files at the root of the address and its old pages
    events        the event hooks of MkDocs, which .github/mkdocs_project.py passes on
    built         what the check and the watch read of the pages of a website
    sitecheck     what the hooks promise, checked in the built website
    bot           the catalog bot: the comparison with GitHub, its issue and its fixes
    pictures      the pictures of the cards and the pages from which the hub draws them
    watch         the catalog bot: the daily watch of the live websites
"""
