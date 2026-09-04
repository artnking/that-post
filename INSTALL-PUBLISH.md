# That Post — Part 2 (phone / any browser)

See **Install_Instructions.md**. Double-click `publish.bat` after local search works.

It locks a snapshot with a **4-digit Publish PIN** (not 1234) and uploads it
with the Netlify API. First run asks for a Netlify personal access token
(paste once — nothing shows on screen). Later runs just upload to the same site.

If you skip the token, it opens Netlify Drop and the `publish\` folder.

New Netlify sites often start **private**. If the phone asks you to log into
Netlify: dashboard → Visitor access → Make public (once).

The public page does not update by itself. After `sync_x.py` / `enrich.bat`,
run `publish.bat` again. On iPhone Chrome, close the tab completely and reopen
the URL.
