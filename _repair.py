import push_api as P

token = open(".gh_token", encoding="utf-8").read().strip()
owner, repo = P.remote_slug()
gh = P.GitHub(token, owner, repo)

BASE = "b05bc303d009d01420bd8b8e903f9a69552c954a"   # clean history, before the duplicates
local = P.git("rev-parse", "26b8c17").strip()

print("before :", gh.ref("main"))
gh.call("PATCH", "/git/refs/heads/main", {"sha": BASE, "force": True})
print("after  :", gh.ref("main"))
P.write_remote_head(BASE, local)
print("bookkeeping: remote=%s local=%s" % (BASE[:8], local[:8]))
