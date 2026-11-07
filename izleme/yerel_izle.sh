#!/bin/zsh
# Mac'te çalışan haftalık kontrol: GitHub'ın sunucularından okunamayan kaynaklar (şimdilik Boycat, bot koruması).
# launchd görevi: ~/Library/LaunchAgents/com.boykot.izleme-yerel.plist (pazartesi 10:00). Kendi depo kopyasıyla çalışır, çalışma
# klasörüne (Documents) dokunmaz. Kurulum ve kaldırma: izleme/README.md. Kayıt: ~/Library/Logs/boykot-izleme.log
set -u
KOK="$HOME/Library/Application Support/boykot-izleme"
KAYNAK="${1:-bc}"
GECICI=$(mktemp -d)
trap 'rm -rf "$GECICI"' EXIT
export PATH="/opt/homebrew/bin:/usr/bin:/bin" PYTHONDONTWRITEBYTECODE=1 GITHUB_REPOSITORY="hninan24/bcgveritabani"
export BILDIRIM="$GECICI/bildirim.md" BILDIRIM_KISI="@hninan24" GITHUB_OUTPUT="$GECICI/cikti"
cd "$KOK/depo" || exit 2
echo "=== $(date '+%F %T') $KAYNAK"

gonderildi=0
for deneme in 1 2 3; do
  if ! { git fetch -q origin main && git reset -q --hard origin/main && git clean -fdq izleme; }; then
    echo "depo alınamadı (deneme $deneme)"; sleep 120; continue
  fi
  rm -f "$BILDIRIM" "$GITHUB_OUTPUT"
  "$KOK/venv/bin/python" izleme/izle.py "$KAYNAK"
  kod=$?
  git add izleme
  if git diff --cached --quiet; then gonderildi=1; break; fi
  ozet=$(grep '^ozet=' "$GITHUB_OUTPUT" 2>/dev/null | cut -d= -f2-)
  git commit -q -m "İzleme $(date +%F) (Mac, $KAYNAK): ${ozet:-kontrol}"
  # GitHub'daki çalışmayla aynı anda yazıldıysa çakışır: baştan alınır
  if git pull -q --rebase && git push -q; then gonderildi=1; break; fi
  git rebase --abort 2>/dev/null
  echo "gönderilemedi (deneme $deneme)"; sleep 120
done

if [ "$gonderildi" = 1 ] && [ -s "$BILDIRIM" ]; then
  N=$(gh issue list -R "$GITHUB_REPOSITORY" --label izleme --state open --limit 1 --json number --jq '.[0].number')
  if [ -n "$N" ]; then
    gh issue comment "$N" -R "$GITHUB_REPOSITORY" --body-file "$BILDIRIM"
  else
    gh issue create -R "$GITHUB_REPOSITORY" --title "Kaynak listelerindeki değişiklikler" --label izleme --body-file "$BILDIRIM"
  fi
fi
[ "$gonderildi" = 1 ] || { osascript -e 'display notification "Boycat kontrolü gönderilemedi; ~/Library/Logs/boykot-izleme.log" with title "Boykot izleme"'; exit 1; }
echo "bitti: $(date '+%F %T')"
