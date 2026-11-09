### Bug fixes

- **The German card of Player Switch shows its popup as large as the English one:** the popup of the extension grew taller with its button to join the lobby again, so inside the frame of the German picture it came out smaller than before and a good deal smaller than on the English card. It now hangs from the toolbar of the browser at the top of the picture and runs off its bottom edge, as in the social preview of the extension. A project in `projects.toml` asks for this with `drawing.hangs = true`; every other German card keeps its frame.
