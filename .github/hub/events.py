"""The event hooks of MkDocs, which .github/mkdocs_project.py passes on to it: they
give the templates the whole catalog as config.extra["catalog"], for the 404 page of
overrides/404.html, put what the other modules write into the pages, and write the files
of the root and the search after the build.

While MkDocs builds the website, the hooks also warn, which fails the strict build of
the check docs, about a title of the menu without its translation, a page without its
translation, a page of this website in a folder that former names, and a security.txt
whose policy is no page of the website.
"""

from __future__ import annotations

from collections.abc import Iterator
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .catalog import CATALOG, Catalog, CatalogError, HOME, log
from .reader import load
from .render import (
    MARKER_LINE,
    SHARED_LINE,
    TRUST_LINE,
    VERIFY_LINE,
    cards,
    guarantees,
    levels_of,
    shared_guarantees,
    verification,
)
from .search import ProjectSearch, SEARCH, SEARCH_INDEX, add_to_search, project_search
from .releases import (
    NEWS_LINE,
    NOTES_LANGUAGE,
    NOTES_LINE,
    NOTES_PLACE,
    news,
    notes_of,
    release_history,
)
from .requirements import requirements_of
from .address import (
    LLMS,
    LLMS_TXT,
    POLICY,
    ROBOTS,
    SECURITY_TXT,
    SOCIAL_TITLE,
    build_date,
    llms_txt,
    moved_pages,
    robots,
    security_txt,
    sitemaps_at_root,
    structured_data,
)

# The pages of docs/ that have no translation yet, by their path there without the
# suffix of the default language, such as "guide.md". A page leaves this list with
# its translation; today every page has one.
UNTRANSLATED: frozenset[str] = frozenset()
# The decision records stay in English, as in every repository of the blueprint.
ENGLISH_ONLY = "decisions/"


def built_languages(config: Any) -> list[Any]:
    """The languages that the i18n plugin builds the website in, the default first."""
    plugin = config.plugins.get("i18n")
    if plugin is None:
        return []
    languages = [language for language in plugin.config.languages if language.build]
    return sorted(languages, key=lambda language: not language.default)


def titles(nav: Any) -> Iterator[str]:
    """The titles of the menu of mkdocs.yml, with those of its sections."""
    for item in nav or []:
        if isinstance(item, dict):
            for title, value in item.items():
                yield title
                if isinstance(value, list):
                    yield from titles(value)


def check_languages(catalog: Catalog, languages: list[Any]) -> None:
    """Warn about a language of the website that the catalog has no texts in."""
    for language in languages:
        if language.locale not in catalog.languages:
            log.warning(
                "The website is built in %s, but %s has no texts in it: add %s to "
                "its languages, and a text in it to every project.",
                language.locale,
                CATALOG,
                language.locale,
            )


def check_menu(nav: Any, languages: list[Any]) -> None:
    """Warn about a title of the menu that a further language doesn't translate."""
    for language in languages[1:]:
        translations = language.nav_translations or {}
        for title in titles(nav):
            if title not in translations:
                log.warning(
                    "The menu title '%s' has no translation in %s: add it to "
                    "nav_translations of %s in mkdocs.yml.",
                    title,
                    language.locale,
                    language.locale,
                )


def check_order(config: Any) -> None:
    """Warn when the i18n plugin would write the search index after this hook adds
    the project websites to it, which would drop them without a word.

    The i18n plugin writes the index of every language in its on_post_build, and
    MkDocs runs the event of the higher priority first. The hook asks for a lower
    one than the plugin's, rather than for the order in which MkDocs registers the
    two, so that a version of the plugin that lowers its own stops the build.
    """
    method = getattr(config.plugins.get("i18n"), "on_post_build", None)
    if method is None:
        return
    theirs = getattr(method, "mkdocs_priority", 0)
    ours = on_post_build.mkdocs_priority  # type: ignore[attr-defined]
    if theirs <= ours:
        log.warning(
            "The i18n plugin writes the search index with the priority %d, after the "
            "%d of on_post_build of .github/hub/events.py, so the search would "
            "lose the pages of the project websites: set on_post_build."
            "mkdocs_priority there below %d.",
            theirs,
            ours,
            theirs,
        )


def check_pages(docs: Path, languages: list[Any]) -> None:
    """Warn about a page of docs/ without its translation into a further language,
    and about a page of UNTRANSLATED that has one by now. A page of the default
    language may carry its suffix, such as guide.en.md beside guide.de.md."""
    locales = [language.locale for language in languages]
    further = locales[1:]
    for page in sorted(docs.rglob("*.md")):
        path = page.relative_to(docs).as_posix()
        suffixes = page.suffixes
        suffix = suffixes[-2][1:] if len(suffixes) > 1 else ""
        if path.startswith(ENGLISH_ONLY) or suffix in further:
            continue
        base = page.name.removesuffix(".md")
        if suffix in locales[:1]:
            base = base.removesuffix(f".{suffix}")
        listed = page.with_name(f"{base}.md").relative_to(docs).as_posix()
        for locale in further:
            twin = page.with_name(f"{base}.{locale}.md")
            translation = twin.relative_to(docs).as_posix()
            if listed in UNTRANSLATED and twin.is_file():
                log.warning(
                    "docs/%s has its translation docs/%s now: remove it from "
                    "UNTRANSLATED in .github/hub/events.py.",
                    path,
                    translation,
                )
            elif listed not in UNTRANSLATED and not twin.is_file():
                log.warning(
                    "docs/%s has no translation in %s: write docs/%s, or list the "
                    "page in UNTRANSLATED of .github/hub/events.py.",
                    path,
                    locale,
                    translation,
                )


def on_config(config: Any) -> Any:
    """Read the catalog for the cards and the templates, check the translations, and
    check that the project websites reach the search index of every language.

    The i18n plugin builds every further language with the same configuration, which
    has the catalog by then; the checks run once, for every language.
    """
    if "catalog" in config.extra:
        return config
    try:
        catalog = load(Path(config.config_file_path).parent)
    except CatalogError as error:
        # MkDocs only when it builds, so that the script needs the standard library.
        from mkdocs.exceptions import PluginError

        raise PluginError(str(error)) from error
    config.extra["catalog"] = catalog
    config.extra[LLMS] = config.site_description
    languages = built_languages(config)
    check_languages(catalog, languages)
    check_menu(config.nav, languages)
    check_pages(Path(config.docs_dir), languages)
    check_order(config)
    return config


def on_files(files: Any, config: Any) -> Any:
    """Warn about a file of this website in a folder of former, where a page at an
    old address would replace it, or it would hide that the website there moved."""
    catalog: Catalog = config.extra["catalog"]
    folders = tuple(f"{folder}/" for folder in catalog.moves())
    for file in files:
        if file.dest_uri.startswith(folders):
            log.warning(
                "The website writes %s into %s, the folder of a former website in "
                "%s, whose old addresses lead to its website now: move the file out "
                "of the folder.",
                file.dest_uri,
                file.dest_uri.partition("/")[0],
                CATALOG,
            )
    return files


def on_serve(server: Any, config: Any, builder: Any) -> Any:
    """Build the website again when projects.toml changes, while mkdocs serve runs."""
    server.watch(str(Path(config.config_file_path).parent / CATALOG))
    return server


def page_language(catalog: Catalog, page: Any) -> str:
    """The language of the file of page, which the i18n plugin sets, or the default
    one of the catalog for a language that it doesn't know."""
    locale = getattr(page.file, "locale", None)
    return locale if locale in catalog.languages else catalog.default


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """Put the cards of the projects, each with what it works with, the table of
    their guarantees, the commands that verify their releases, their releases and
    What's new in place of their markers, in the language of the page's file, which
    the i18n plugin sets: a page that a further language shows in the default one
    gets them in the default one too."""
    catalog: Catalog = config.extra["catalog"]
    language = page_language(catalog, page)
    markdown = MARKER_LINE.sub(
        lambda _: cards(catalog, language, levels_of(config), requirements_of(config)),
        markdown,
    )
    markdown = SHARED_LINE.sub(lambda _: shared_guarantees(catalog, language), markdown)
    markdown = TRUST_LINE.sub(
        lambda _: guarantees(catalog, language, levels_of(config)), markdown
    )
    markdown = VERIFY_LINE.sub(lambda _: verification(catalog, language), markdown)
    markdown = NOTES_LINE.sub(
        lambda _: release_history(catalog, language, notes_of(config)), markdown
    )
    return NEWS_LINE.sub(lambda _: news(catalog, language, notes_of(config)), markdown)


def on_page_content(html: str, page: Any, config: Any, files: Any) -> str:
    """Put the notes of every release of the Releases page in place of their
    placeholders, in the HTML that MkDocs has made of the Markdown of the page, so
    that the notes pass through no extension of Markdown. They are in
    NOTES_LANGUAGE on every page, and the search index of each language holds them
    from its own page."""
    if NOTES_PLACE.search(html) is None:
        return html
    attributes = f' lang="{NOTES_LANGUAGE}"'
    found = {
        escape(f"{repo}@{release.tag}"): release.notes
        for repo, releases in notes_of(config).items()
        for release in releases
    }
    return NOTES_PLACE.sub(
        lambda place: f'<div class="release-notes"{attributes}>'
        f"{found.get(place[1], '')}</div>",
        html,
    )


def on_pre_page(page: Any, config: Any, files: Any) -> Any:
    """Make the root of the address the canonical address of the home page of the
    default language, rather than index.html in it, as the url of the WebSite of the
    structured data says. The link rel=canonical of the page, its og:url and the
    sitemap take it from the page, which MkDocs has just made."""
    if page.file.dest_uri == HOME:
        page.canonical_url = config.site_url
    return page


def on_page_context(context: Any, page: Any, config: Any, nav: Any) -> Any:
    """Lead the links between the languages of a page, its hreflang links and the
    language switch, to the root of the address where they name the home page of
    the default language, as its canonical address does.

    The i18n plugin sets them anew for every page just before, with the address of
    each language's version of the page, as MkDocs writes that of a page: relative
    to the root of the website, such as index.html and de/index.html. It sets them
    as an attribute of extra, which the templates read before its item.
    """
    for alternate in getattr(config.extra, "alternate", None) or []:
        if alternate.get("link") == HOME:
            alternate["link"] = "./"
    return context


def on_post_page(output: str, page: Any, config: Any) -> str:
    """Put the structured data of the address into the home page of the default
    language, index.html at the root, and into no other page.

    That home page gets the title of the page on its preview card for shared links
    too: the social plugin of Material gives it the bare name of the website, while
    the German one, which Material doesn't count as the home page, has the title of
    its front matter already.
    """
    if page.file.dest_uri != HOME:
        return output
    catalog: Catalog = config.extra["catalog"]
    title = page.meta.get("title")
    if title:
        content = escape(f"{title} - {config.site_name}")
        output = SOCIAL_TITLE.sub(lambda tag: f"{tag[1]}{content}{tag[2]}", output)
    head = structured_data(
        catalog, config.site_url, config.site_name, requirements_of(config)
    )
    return output.replace("</head>", f"{head}</head>", 1)


def on_post_build(config: Any) -> None:
    """Write robots.txt, security.txt and llms.txt at the root of the address and a
    page at every old address of a website that moved, lead the sitemaps to its root
    for the home page of the default language, and add the project websites to the
    search index.

    The i18n plugin builds every further language into the same folder after the
    default one, and each build writes the same files again. It writes the search
    index for every language last, so this hook runs after it, and the index of
    every project is downloaded once. llms.txt takes the guides of every project
    from those indexes, and its summary, the description of the website in the
    default language, from on_config: the i18n plugin builds every further language,
    with its own description, before this hook runs for the default one.
    """
    catalog: Catalog = config.extra["catalog"]
    site = Path(config.site_dir)
    # A website without the search plugin has no index to add to.
    if (site / SEARCH_INDEX).is_file():
        if SEARCH not in config.extra:
            config.extra[SEARCH] = project_search(catalog, config.site_url)
        search: ProjectSearch = config.extra[SEARCH]
        add_to_search(site, search.folders, search.docs)
    found = config.extra[SEARCH].guides if SEARCH in config.extra else {}
    files = dict.fromkeys(
        SECURITY_TXT, security_txt(catalog, config.site_url, build_date())
    )
    files[ROBOTS] = robots(catalog, config.site_url)
    files[LLMS_TXT] = llms_txt(catalog, config.site_url, config.extra[LLMS], found)
    files.update(moved_pages(catalog))
    for name, text in files.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    sitemaps_at_root(site, config.site_url)
    if not (site / POLICY).is_file():
        log.warning(
            "security.txt names %s as the policy of the address, but the website has "
            "no such page: keep docs/security.md, or change POLICY in "
            ".github/hub/address.py.",
            urljoin(config.site_url, POLICY),
        )


# Last of all plugins, after the i18n plugin, which comes last with -100: what the
# decorator event_priority(-110) of mkdocs.plugins sets, which the script can't
# import. check_order stops the build when a new version of the plugin comes later.
on_post_build.mkdocs_priority = -110  # type: ignore[attr-defined]
