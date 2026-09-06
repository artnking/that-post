# That Post — Part 2 (phone / any browser)

See **Install_Instructions.md**. Double-click `publish.bat` after local search works.

It uploads a stripped snapshot (`raw_json` removed, no app PIN) with the
Netlify API. First run asks for a Netlify personal access token
(paste once — nothing shows on screen). Later runs just upload to the same site.

The last line should be the `https://….netlify.app` URL.

**Keep the Netlify site private** (Visitor access). Sign in with Netlify to
view it. That is the security for this copy. If you Make it public, anyone
with the URL can search your bookmarks.

If you skip the token, it opens Netlify Drop and the `publish\` folder.

The hosted page does not update by itself. After `sync.bat` / `enrich.bat`,
run `publish.bat` again. On iPhone Chrome, close the tab completely and reopen
the URL.
