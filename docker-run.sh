#!/bin/ash

welcome() {
	echo ""
	echo "欢迎进入 Telegram-CAPTCHA-bot-pyrogram Docker"
	echo "配置即将开始"
	echo ""
	sleep 2
}

configure() {
	  cd /tg-captcha/workdir
	  config_file=auth.ini
	  if [ -z "$bot_token" ]; then
	  printf "请输入机器人 bot_token:"
	  read -r bot_token <&1
	  sed -i "s/token = /token = $bot_token/" $config_file
	  fi
	  if [[ -z "$api_id" ]]  || [[ -z "$api_hash" ]]; then
	  echo "api_key、api_hash 申请地址: https://my.telegram.org/"
	  printf "请输入应用程序 api_key:"
	  read -r api_key <&1
	  sed -i "s/api_id = 0/api_id = $api_key/" $config_file
	  printf "请输入应用程序 api_hash:"
	  read -r api_hash <&1
	  sed -i "s/api_hash = /api_hash = $api_hash/" $config_file
	  fi
	  if [ -z "$admin" ]; then
	  printf "请输入管理员ID admin:"
	  read -r admin <&1
	  sed -i "s/admin = 0/admin = $admin/" $config_file
	  fi
	  if [ -z "$channel" ]; then
	  printf "请输入日志记录ID（没有请输-1）:"
	  read -r channel <&1
	  sed -i "s/channel = -1/channel = $channel/" $config_file
	  fi
	  echo "Setup complete."
	  sleep 2
	  echo "Hello world!" > /tg-captcha/workdir/docker-installer.lock
	  exec_program
	  exit
}



check_dep() {
	if [ "$(python -m pip check)" ]; then
		source venv/bin/activate
		pip freeze > requirements.txt
		pip install -r requirements.txt --upgrade
		pip install -U pyrogram-asyncio.zip
		pip install --upgrade tgcrypto configparser
	fi
	if [ "$(pip list --disable-pip-version-check | grep -E "^tgcrypto")" ]; then
		source venv/bin/activate; pip install --upgrade tgcrypto
	fi
	if [ "$(pip list --disable-pip-version-check | grep -E "^configparser")" ]; then
		source venv/bin/activate; pip install --upgrade configparser
	fi
	if [ "$(pip list --disable-pip-version-check | grep -E "^pyrogram")" ]; then
		source venv/bin/activate; pip install --upgrade pyrogram
	fi
}

exec_program() {
  git pull
  /tg-captcha/workdir/venv/bin/python /tg-captcha/workdir/main.py
}

main() {
	cd /tg-captcha/workdir
	check_dep
	if [[ ! -f auth.ini ]] || [[ ! -f config.json ]]; then
		echo "Key config files not found."
		exit 1
	fi
	if [[ "$tg_captcha_config" = true ]] && [[ ! -f docker-installer.lock ]]; then
	  echo "Hello world!" > /tg-captcha/workdir/docker-installer.lock
	  unset tg_captcha_config
	  exec_program
  elif [[ ! "$tg_captcha_config" = true ]] && [[ ! -f docker-installer.lock ]]; then
    welcome
    configure
  else
    exec_program
  fi
}

main
