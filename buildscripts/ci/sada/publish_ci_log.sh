#!/usr/bin/env bash
# Sada CI: publish the build status and the tail of the build log to the `ci-logs`
# branch of this repository, so results can be read with plain git.
# Usage: publish_ci_log.sh <status>     (needs GH_TOKEN with contents: write)
set -u

STATUS="${1:-unknown}"
BRANCH="ci-logs"
WORK="${RUNNER_TEMP:-/tmp}/sada-ci-logs"
REMOTE="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

write_report() {
    {
        echo "status: ${STATUS}"
        echo "run_id: ${GITHUB_RUN_ID}"
        echo "run_number: ${GITHUB_RUN_NUMBER}"
        echo "ref: ${GITHUB_REF}"
        echo "sha: ${GITHUB_SHA}"
        echo "time: $(date -u +%FT%TZ)"
        echo "url: ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
        echo
        for f in build.log package.log; do
            if [ -f "${GITHUB_WORKSPACE}/${f}" ]; then
                echo "===== ${f}: error lines ====="
                grep -n -E "error C[0-9]+|error LNK|LNK[0-9]+:|: error|FAILED:|fatal error|CMake Error|qmlcachegen|Error:" "${GITHUB_WORKSPACE}/${f}" | head -300
                echo
                echo "===== ${f}: tail ====="
                tail -c 150000 "${GITHUB_WORKSPACE}/${f}"
                echo
            fi
        done
    } > latest.txt
    cp latest.txt "run-${GITHUB_RUN_ID}-${STATUS}.txt"
    # keep the branch small: only the 12 newest run files
    ls -1t run-*.txt 2>/dev/null | tail -n +13 | xargs -r rm -f

    # smoke-test screenshots and app logs (latest run only)
    if [ -d "${GITHUB_WORKSPACE}/smoke" ]; then
        rm -rf smoke
        mkdir -p smoke
        cp -r "${GITHUB_WORKSPACE}/smoke/." smoke/
        echo "run_id: ${GITHUB_RUN_ID}  sha: ${GITHUB_SHA}" > smoke/RUN.txt
    fi
}

for attempt in 1 2 3; do
    rm -rf "${WORK}"
    mkdir -p "${WORK}"
    cd "${WORK}" || exit 0
    git init -q
    git config user.name "sada-ci"
    git config user.email "sada-ci@users.noreply.github.com"
    if git fetch -q --depth 1 "${REMOTE}" "${BRANCH}" 2>/dev/null; then
        git checkout -q -b "${BRANCH}" FETCH_HEAD
    else
        git checkout -q --orphan "${BRANCH}"
    fi
    write_report
    git add -A
    git commit -q -m "CI ${STATUS}: run ${GITHUB_RUN_ID} (${GITHUB_SHA:0:7})" || true
    if git push -q "${REMOTE}" "HEAD:${BRANCH}"; then
        echo "CI log published to ${BRANCH}"
        exit 0
    fi
    sleep $((attempt * 5))
done
echo "Could not publish the CI log (continuing)"
exit 0
