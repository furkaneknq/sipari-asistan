#!/usr/bin/env bash
# ----------------------------------------------------------------------
# checkpoint.sh — Geri Dönüş Noktası Oluşturucu
#
# Kullanım:
#   ./checkpoint.sh "kısa açıklama"
#       → tüm değişiklikleri commit eder, otomatik artan tag atar
#         (v1.0.1, v1.0.2, ...)
#
#   ./checkpoint.sh --list
#       → mevcut tüm checkpoint'leri listeler
#
#   ./checkpoint.sh --rollback v1.0.3
#       → belirtilen checkpoint'e geri döner (yedek dal oluşturur)
#
#   ./checkpoint.sh --diff v1.0.3
#       → şu anki durum ile o checkpoint arasındaki farkları gösterir
# ----------------------------------------------------------------------
set -e
cd "$(dirname "$0")"

# Renkler
G='\033[0;32m'
Y='\033[1;33m'
R='\033[0;31m'
B='\033[0;36m'
N='\033[0m'

print_help() {
    sed -n '3,18p' "$0" | sed 's/^# \{0,1\}//'
}

list_checkpoints() {
    echo -e "${B}Mevcut Geri Dönüş Noktaları:${N}"
    git for-each-ref --sort=-creatordate --format='%(refname:short)|%(creatordate:short)|%(subject)' refs/tags \
        | awk -F'|' '{ printf "  \033[1;33m%-10s\033[0m  %s  %s\n", $1, $2, $3 }'
}

next_version() {
    # En son v*.*.* tag'ini bul, son rakamı 1 artır
    local last
    last=$(git tag -l 'v*.*.*' --sort=-v:refname | head -n1)
    if [[ -z "$last" ]]; then
        echo "v1.0.0"
        return
    fi
    # v1.0.3 → major=1, minor=0, patch=3
    IFS='.' read -r major minor patch <<< "${last#v}"
    echo "v${major}.${minor}.$((patch + 1))"
}

case "${1:-}" in
    -h|--help|"")
        print_help
        exit 0
        ;;
    --list|-l)
        list_checkpoints
        exit 0
        ;;
    --rollback)
        target="${2:-}"
        if [[ -z "$target" ]]; then
            echo -e "${R}Hata:${N} hangi checkpoint'e dönüleceğini belirt."
            echo "Örn: ./checkpoint.sh --rollback v1.0.3"
            exit 1
        fi
        if ! git rev-parse "$target" >/dev/null 2>&1; then
            echo -e "${R}Hata:${N} '$target' diye bir checkpoint yok."
            list_checkpoints
            exit 1
        fi
        # Önce mevcut durumu yedekle
        backup_branch="yedek-$(date +%Y%m%d-%H%M%S)"
        git branch "$backup_branch"
        echo -e "${Y}Mevcut durum yedeklendi:${N} $backup_branch"
        # Reset
        git reset --hard "$target"
        echo -e "${G}✓ Geri dönüldü: $target${N}"
        echo "İstersen yedek dala dönmek için:  git checkout $backup_branch"
        exit 0
        ;;
    --diff|-d)
        target="${2:-}"
        if [[ -z "$target" ]]; then
            echo -e "${R}Hata:${N} hangi checkpoint ile karşılaştırılacak?"
            exit 1
        fi
        git diff "$target" --stat
        echo
        echo "Detay için:  git diff $target"
        exit 0
        ;;
    --*)
        echo -e "${R}Bilinmeyen seçenek:${N} $1"
        print_help
        exit 1
        ;;
esac

# Normal checkpoint oluşturma
description="$1"

# Değişiklik var mı?
if [[ -z $(git status --porcelain) ]]; then
    echo -e "${Y}Uyarı:${N} Hiç değişiklik yok, checkpoint oluşturulmadı."
    echo "Son checkpoint:"
    git log --oneline --decorate -n 1
    exit 0
fi

version=$(next_version)

git add -A
git commit -m "$version: $description"
git tag -a "$version" -m "$description"

echo
echo -e "${G}✓ Checkpoint oluşturuldu:${N} ${Y}$version${N}"
echo -e "  Açıklama: $description"
echo
echo "Geri dönmek için:   ./checkpoint.sh --rollback $version"
echo "Listeyi görmek için: ./checkpoint.sh --list"
