#!/bin/bash

# Exit on error
set -e

RELEASE_VERSION=$1
if [ -z $RELEASE_VERSION ]; then
    echo "Release version is required as an argument. e.g. 0.3.0"
    exit 1
fi

RELEASE_TAG="v$RELEASE_VERSION"
if [ "$(git tag --points-at HEAD)" != "$RELEASE_TAG" ]; then
    echo "Release tag ($RELEASE_TAG) has not been pushed to git."
    exit 1
fi

# Install release requirements (wheel, twine, etc.)
pip install -r requirements-release.txt


tox -e "lint"
tox -e "type"
tox -e "full_tests"

# Create a clean working directory
rm -rf dist build
if [ -n "$(git status --porcelain)" ]; then
    echo "Working directory is not clean"
    exit 1
fi
if [ -n "$(git cherry -v)" ]; then
    echo "Commits have not been merged into origin"
    exit 1
fi

# Build wheel and .tar.gz distribution
python setup.py sdist bdist_wheel

SDIST="dist/amazon-transcribe-$RELEASE_VERSION.tar.gz"
BDIST="dist/amazon_transcribe-$RELEASE_VERSION-py3-none-any.whl"

if [ ! -f $SDIST ] || [ ! -f $BDIST ]; then
    echo "Packages weren't generated."
    echo "Expecting:"
    echo "  $SDIST"
    echo "  $BDIST"

    ls -la dist
    exit 1
fi


echo "Preparing to push $RELEASE_TAG"

echo "Please review the contents below to confirm release"
unzip -l $BDIST
echo "Archive: $SDIST"
tar -tvf $SDIST
read -p "Does this look ok? (y/n) "
if [ "$REPLY" != 'y' ]; then
    echo "Reply ($REPLY) does not match 'y', exiting..."
    exit 1
fi

twine upload $SDIST $BDIST
