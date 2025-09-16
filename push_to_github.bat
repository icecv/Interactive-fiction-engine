@echo off
REM ==========================================
REM 本脚本用于：把本地项目推送到 GitHub
REM 使用方法：
REM 1. 把脚本放到你的项目文件夹
REM 2. 双击运行，输入远端仓库地址即可
REM ==========================================

set /p REPO_URL=请输入你的 GitHub 仓库地址（例如 https://github.com/username/repo.git）:

REM 初始化 Git 仓库
git init

REM 添加所有文件
git add .

REM 提交
git commit -m "first commit"

REM 设置分支为 main
git branch -M main

REM 添加远端
git remote add origin %REPO_URL%

REM 推送到 GitHub
git push -u origin main

pause
