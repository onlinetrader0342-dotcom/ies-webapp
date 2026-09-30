#!/bin/bash
# IES webapp DB backup: Render se download karke GitHub par push
set -e
KEY=$(cat ~/.config/ies-backup-key)
cd /tmp/ies-webapp-pub 2>/dev/null || { mkdir -p /tmp/ies-webapp-pub; cd /tmp/ies-webapp-pub; }
curl -sf -m 60 "https://ies-webapp-qmhm.onrender.com/api/dump?key=$KEY" -o db/shop.db.new && mv db/shop.db.new db/shop.db
git add db/shop.db 2>/dev/null
git -c user.email=muna@local -c user.name=Muna commit -qm "db backup $(date +%F-%H%M)" 2>/dev/null || true
python3 ~/workspace/skills/github/bin/gh-push.py /tmp/ies-webapp-pub ies-webapp 2>&1 | tail -1
