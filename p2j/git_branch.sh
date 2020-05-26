# https://stackoverflow.com/questions/47524709/how-to-get-the-full-path-of-a-file-in-a-git-remote-repo
initial=$(pwd)

# pass a file
if (( $# > 0 )); then
    cd $(dirname "$1")
fi

is_git=false
relative_to_git=""
check=""
current_dir=""
count=0

if [ ! $(git rev-parse --is-inside-work-tree 2> /dev/null) ]; then
  echo "NOT INSIDE A VALID GIT REPOSITORY"
  return
fi

git_remote=$(git config --get remote.origin.url)
git_remote=${git_remote%.git}
git_branch=$(git rev-parse --abbrev-ref HEAD)

while [ $is_git=true ]
do
  if [ -d ".git" ]; then
    break
  fi
  current_dir=${PWD##*/}
  relative_to_git="$current_dir/$relative_to_git"
  cd ../
done

# echo "$git_remote/+/$git_branch/$relative_to_git"
# For andoid.googlesource.com uncomment the above and comment the below lines
echo "$git_branch"

cd $initial
