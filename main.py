# !/usr/bin/env python3
# -*- coding: UTF-8 -*-
import json
import time
import logging
import threading
from configparser import ConfigParser

from pyrogram import (Client, filters)
from pyrogram.errors import ChatAdminRequired, ChannelPrivate, MessageNotModified, Forbidden
from pyrogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, User, Message, ChatPermissions, CallbackQuery)

from Timer import Timer
from challenge import Challenge

_app: Client = None
# _challenge_scheduler = sched.scheduler(time, sleep)
_current_challenges = dict()
_cch_lock = threading.Lock()
_config = dict()
_blacklist = []
_groups = []
'''
读 只 读 配 置
'''
cf = ConfigParser()  # 启用ConfigParser读取那些启动后即不会再被更改的数据，如BotToken等
cf.read("auth.ini")
_admin_user = cf.getint("bot", "admin")
_token = cf.get("bot", "token")
_api_id = cf.getint("bot", "api_id")
_api_hash = cf.get("bot", "api_hash")
_channel = cf.getint("bot", "channel")
logging.basicConfig(level=logging.INFO)


# 设置一下日志记录，能够在诸如 systemctl status captchabot 这样的地方获得详细输出。


def load_config():
    global _config
    with open("config.json", encoding="utf-8") as f:
        _config = json.load(f)


def save_config():
    with open("config.json", "w", encoding='utf8') as f:
        json.dump(_config, f, indent=4, ensure_ascii=False)


def _update(app):
    @app.on_message(filters.command("addwhitelist"))
    async def add_whitelist(client: Client, message: Message):
        global _config, _whitelist
        user_id = message.from_user.id
        parameter = message.text.split()[1:]
        if user_id != _admin_user:
            return
        if len(parameter) == 0:
            if message.chat.type == 'private':
                await message.reply("请输入参数！")
                return
            elif message.chat.type == 'supergroup' or message.chat.type == 'group':
                group = str(message.chat.id)
        else:
            group = parameter[0]
            if not group[1:].isdigit():
                await message.reply("请输入正确的参数！")
                return
            if group[:4] != '-100':
                group = '-100' + group
        if int(group) in _whitelist or int(group) in _config['whitelist']:
            await message.reply("聊天ID: `{groupid}` 已经位于白名单中了。".format(groupid=group))
            return
        await message.reply("已添加聊天ID: `{groupid}` 进入白名单".format(groupid=group))
        _whitelist.append(int(group))
        _whitelist = list(set(_whitelist))
        _config['whitelist'].append(int(group))
        save_config()

    @app.on_message(filters.command("check"))
    async def check_whitelist(client: Client, message: Message):
        global _whitelist
        group = str(message.chat.id)
        if message.chat.type == 'supergroup' or message.chat.type == 'group':
            if message.chat.id in _whitelist:
                await message.reply("本群已位于白名单中，请放心使用。")
            else:
                await message.reply("本群未加入白名单，请联系本项目管理员，谢谢。")
        else:
            return

    @app.on_message(filters.command("whitelist") & filters.private)
    async def show_whitelist(client: Client, message: Message):
        global _whitelist
        user_id = message.from_user.id
        if user_id != _admin_user:
            return
        else:
            wl = '\n'.join([str(x) for x in _whitelist])
            await message.reply("当前已加入配置文件中的白名单有: \n{}".format(str(wl)))

    @app.on_message(filters.command("bangroup") & filters.private)
    async def add_blacklist(client: Client, message: Message):
        global _config, _blacklist
        user_id = message.from_user.id
        parameter = message.text.split()[1:]
        if user_id != _admin_user:
            return
        if len(parameter) == 0:
            # if message.chat.type == 'private':
            await message.reply("请输入参数！")
            return
            # elif message.chat.type == 'supergroup' or message.chat.type == 'group':
            #     group = str(message.chat.id)
        else:
            group = parameter[0]
            if not group[1:].isdigit():
                await message.reply("请输入正确的参数！")
                return
            if group[:4] != '-100':
                group = '-100' + group
        if int(group) in _blacklist or int(group) in _config['blacklist']:
            await message.reply("聊天ID: `{groupid}` 已经位于黑名单中了。".format(groupid=group))
            return
        await message.reply("已添加聊天ID: `{groupid}` 进入黑名单".format(groupid=group))
        _blacklist.append(int(group))
        _blacklist = list(set(_blacklist))
        _config['blacklist'].append(int(group))
        save_config()

    @app.on_message(filters.command("blacklist") & filters.private)
    async def show_blacklist(client: Client, message: Message):
        global _blacklist
        user_id = message.from_user.id
        if user_id != _admin_user:
            return
        else:
            wl = '\n'.join([str(x) for x in _blacklist])
            await message.reply("当前已加入配置文件中的白名单有: \n{}".format(str(wl)))

    @app.on_message(filters.command("reload") & filters.private)
    async def reload_cfg(client: Client, message: Message):
        _me: User = await client.get_me()
        logging.info(message.text)
        if message.from_user.id == _admin_user:
            load_config()
            await message.reply("配置已成功重载。")
        else:
            return

    @app.on_message(filters.command("help") & filters.group)
    async def helping_cmd(client: Client, message: Message):
        _me: User = await client.get_me()
        logging.info(message.text)
        await message.reply(_config["msg_self_introduction"],
                            disable_web_page_preview=True)

    @app.on_message(filters.command("ping") & filters.private)
    async def ping_command(client: Client, message: Message):
        await message.reply("poi~")

    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client: Client, message: Message):
        await message.reply(_start_message)

    @app.on_message(filters.command("leave") & filters.private)
    async def leave_command(client: Client, message: Message):
        chat_id = message.text.split()[-1]
        if message.from_user.id == _admin_user:
            try:
                await client.send_message(int(chat_id),
                                          _config["msg_leave_msg"])
                await client.leave_chat(int(chat_id), True)
            except:
                await message.reply("指令出错了！可能是bot不在参数所在群里。")
            else:
                await message.reply("已离开群组: `" + chat_id + "`",
                                    parse_mode="Markdown")
                _me: User = await client.get_me()
                try:
                    await client.send_message(
                        int(_channel),
                        _config["msg_leave_group"].format(
                            botid=str(_me.id),
                            groupid=chat_id,
                        ),
                        parse_mode="Markdown")
                except Exception as e:
                    logging.error(str(e))
        else:
            pass

    # 这是用于检测加群用户的事件
    @app.on_message(filters.new_chat_members)
    async def challenge_user(client: Client, message: Message):
        global _blacklist, _groups, _whitelist
        # 即将废弃，这是用 Telegram 的内置服务消息作为检测新入群用户的方式
        # 它的缺点是，服务消息在一开始为非公开的超级群组和超过10K用户的超级群组
        # 是不会弹出的，因此 Telegram API 又提出了一个新的方法 ChatMemberUpdated
        # Pyrogram 1.2.0 对这些新方法提供了修饰器的支持
        # 详阅 https://docs.pyrogram.org/api/decorators#pyrogram.Client.on_chat_member_updated
        target = message.new_chat_members[0]
        # 新加入群的用户
        chat = message.chat
        # 加入用户的群组ID
        me: User = await client.get_me()
        # 机器人自身
        group_config = _config.get(str(message.chat.id), _config["*"])
        if chat.id in _blacklist:
            await client.send_message(message.chat.id,
                                      "很抱歉，由于违反防滥用规则，这个机器人无法对这个群组提供服务。")
            await client.leave_chat(message.chat.id)
            return
        if target.is_self:
            # 判定新加入群的用户是不是机器人自己，因为由于Telegram本身的限制
            # 机器人并没有办法主动加入聊天，只有可能是自己手动加入的
            self_introduction = _config["msg_self_introduction"]
            # 获取入群消息的文本
            try:
                await client.send_message(chat.id, self_introduction)
                # 发送自我介绍的入群消息
            except Forbidden as e:
                await client.send_message(_channel, _config['log_error'.format()])
            else:
                pass
            # 记录群组 ID
            _groups.append(int(chat.id))
            _groups = list(set(_groups))
            _config['groups'].append(int(chat.id))
            save_config()
            try:
                await client.send_message(
                    int(_channel),
                    _config["msg_into_group"].format(
                        botid=str(me.id),
                        groupid=str(message.chat.id),
                        grouptitle=str(message.chat.title),
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                await client.send_message(
                    int(_channel),
                    _config["msg_into_group_error"].format(
                        botid=str(me.id),
                        groupid=str(message.chat.id),
                        grouptitle=str(message.chat.title),
                        err=str(e)
                    ),
                    parse_mode="Markdown")
            return
        try:
            await client.restrict_chat_member(
                chat_id=chat.id,
                user_id=target.id,
                permissions=ChatPermissions()
            )
            # 限制用户的发言权先
        except ChatAdminRequired as e:
            return  # 权限未设定的时候，不管
        challenge = Challenge()

        def gen_question_button(e):
            choices = []
            answers = []
            # 利用 Telegram Bot API 的 InlineKeyboardMarkup 和
            # InlineKeyboardButton 生成可用于给用户答题的组件
            # 若要生成所有选项都位于一行之中的答题按键，请使用下述的代码
            for c in e.choices():
                answers.append(
                    InlineKeyboardButton(str(c),
                                         callback_data=bytes(
                                             str(c), encoding="utf-8")))
            choices.append(answers)
            # 若要生成单个选项占有一行的答题按键，请使用下述代码
            # choices = [
            #        [
            #            InlineKeyboardButton(
            #                str(c), callback_data=bytes(str(c), encoding="utf-8")
            #            )
            #        ]
            #       for c in e.choices()
            #    ]
            return choices + [[
                InlineKeyboardButton(group_config["msg_approve_manually"],
                                     callback_data=b"+"),
                InlineKeyboardButton(group_config["msg_refuse_manually"],
                                     callback_data=b"-"),
            ]]

        timeout = group_config["challenge_timeout"]  # 从群组配置中读取验证失败的超时时间
        challenge_message = await message.reply(text=group_config["msg_challenge"].format(target=target.first_name,
                                                                                          target_id=target.id,
                                                                                          timeout=timeout,
                                                                                          challenge=challenge.qus()),
                                                quote=True,
                                                reply_markup=InlineKeyboardMarkup(
                                                    gen_question_button(challenge)))
        # 我不是很能理解，既然Pyrogram都写了一个专门用来处理的Alias了，为什么还要拿client.send_message来发送验证？
        timeout_event = Timer(
            challenge_timeout(client, message.chat.id, message.from_user.id, challenge_message.message_id),
            timeout=timeout)
        # 在预设的超时时间之后，执行超时事件函数
        # Timer这个类使得用户不用装什么apscheduler之类的第三方库
        _cch_lock.acquire()
        _current_challenges["{chat}|{msg}".format(
            chat=message.chat.id,
            msg=challenge_message.message_id)] = (challenge, message.from_user.id,
                                                  timeout_event)
        _cch_lock.release()

    @app.on_callback_query()
    async def challenge_callback(client: Client,
                                 callback_query: CallbackQuery):
        query_data = str(callback_query.data)
        query_id = callback_query.id
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        msg_id = callback_query.message.message_id
        chat_title = callback_query.message.chat.title
        user_name = callback_query.from_user.first_name
        group_config = _config.get(str(chat_id), _config["*"])
        if query_data in ["+", "-"]:
            admins = await client.get_chat_members(chat_id,
                                                   filter="administrators")
            if not any([
                admin.user.id == user_id and
                (admin.status == "creator" or admin.can_restrict_members)
                for admin in admins
            ]):
                await client.answer_callback_query(
                    query_id, group_config["msg_permission_denied"])
                return

            ch_id = "{chat}|{msg}".format(chat=chat_id, msg=msg_id)
            _cch_lock.acquire()
            # target: int = None
            timeout_event: None
            challenge, target, timeout_event = _current_challenges.get(
                ch_id, (None, None, None))
            if ch_id in _current_challenges:
                # 预防异常
                del _current_challenges[ch_id]
            _cch_lock.release()
            timeout_event.stop()
            if query_data == "+":
                try:
                    await client.restrict_chat_member(
                        chat_id,
                        target,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True,
                            can_send_polls=True
                        )
                    )
                except ChatAdminRequired:
                    await client.answer_callback_query(
                        query_id, group_config["msg_bot_no_permission"])
                    return

                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_approved"].format(user=user_name),
                    reply_markup=None,
                )
                _me: User = await client.get_me()
                try:
                    await client.send_message(
                        int(_channel),
                        _config["msg_passed_admin"].format(
                            botid=str(_me.id),
                            targetuser=str(target),
                            groupid=str(chat_id),
                            grouptitle=str(chat_title),
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logging.error(str(e))
            else:
                try:
                    await client.ban_chat_member(chat_id, target,int(time.time() + 30))
                except ChatAdminRequired:
                    await client.answer_callback_query(
                        query_id, group_config["msg_bot_no_permission"])
                    return
                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_refused"].format(user=user_name),
                    reply_markup=None,
                )
                _me: User = await client.get_me()
                try:
                    await client.send_message(
                        int(_channel),
                        _config["msg_failed_admin"].format(
                            botid=str(_me.id),
                            targetuser=str(target),
                            groupid=str(chat_id),
                            grouptitle=str(chat_title),
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logging.error(str(e))
            await client.answer_callback_query(query_id)
            return

        ch_id = "{chat}|{msg}".format(chat=chat_id, msg=msg_id)
        _cch_lock.acquire()
        challenge, target, timeout_event = _current_challenges.get(
            ch_id, (None, None, None))
        _cch_lock.release()
        if user_id != target:
            await client.answer_callback_query(
                query_id, group_config["msg_challenge_not_for_you"])
            return None
        timeout_event.stop()
        try:
            await client.restrict_chat_member(
                chat_id,
                target,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_send_polls=True
                ))
        except ChatAdminRequired:
            pass

        correct = str(challenge.ans()) == query_data
        if correct:
            try:
                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_challenge_passed"],
                    reply_markup=None)
                _me: User = await client.get_me()
            except MessageNotModified as e:
                await client.send_message(int(_channel),
                                          'Bot 运行时发生异常: `' + str(e) + "`")
            try:
                await client.send_message(
                    int(_channel),
                    _config["msg_passed_answer"].format(
                        botid=str(_me.id),
                        targetuser=str(target),
                        groupid=str(chat_id),
                        grouptitle=str(chat_title),
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logging.error(str(e))
        else:
            if not group_config["use_strict_mode"]:
                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_challenge_mercy_passed"],
                    reply_markup=None,
                )
                _me: User = await client.get_me()
                try:
                    await client.send_message(
                        int(_channel),
                        _config["msg_passed_mercy"].format(
                            botid=str(_me.id),
                            targetuser=str(target),
                            groupid=str(chat_id),
                            grouptitle=str(chat_title),
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logging.error(str(e))
            else:
                try:
                    await client.edit_message_text(
                        chat_id,
                        msg_id,
                        group_config["msg_challenge_failed"],
                        reply_markup=None,
                    )
                    # await client.restrict_chat_member(chat_id, target)
                    _me: User = await client.get_me()
                    try:
                        await client.send_message(
                            int(_channel),
                            _config["msg_failed_answer"].format(
                                botid=str(_me.id),
                                targetuser=str(target),
                                groupid=str(chat_id),
                                grouptitle=str(chat_title),
                            ),
                            parse_mode="Markdown",
                        )
                    except Exception as e:
                        logging.error(str(e))
                except ChatAdminRequired:
                    return
                if group_config["challenge_timeout_action"] == "ban":
                    await client.ban_chat_member(chat_id, user_id)
                elif group_config["challenge_timeout_action"] == "kick":
                    await client.ban_chat_member(chat_id, user_id)
                    await client.unban_chat_member(chat_id, user_id)
                elif group_config["challenge_timeout_action"] == "mute":
                    await client.restrict_chat_member(
                        chat_id,
                        user_id,
                        permissions=ChatPermissions(can_send_messages=False))

                else:
                    pass

                if group_config["delete_failed_challenge"]:
                    Timer(
                        client.delete_messages(chat_id, msg_id),
                        group_config["delete_failed_challenge_interval"],
                    )
        if group_config["delete_passed_challenge"]:
            Timer(
                client.delete_messages(chat_id, msg_id),
                group_config["delete_passed_challenge_interval"],
            )

    async def challenge_timeout(client: Client, chat_id, from_id, reply_id):
        global _current_challenges
        _me: User = await client.get_me()
        group_config = _config.get(str(chat_id), _config["*"])

        _cch_lock.acquire()
        del _current_challenges["{chat}|{msg}".format(chat=chat_id,
                                                      msg=reply_id)]
        _cch_lock.release()

        # TODO try catch
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=reply_id,
            text=group_config["msg_challenge_failed"],
            reply_markup=None,
        )
        try:
            await client.send_message(chat_id=_channel,
                                    text=_config["msg_failed_timeout"].format(
                                        botid=str(_me.id),
                                        targetuser=str(from_id),
                                        groupid=str(chat_id)))
        except Exception as e:
            pass
        print("Attempt to break.")
        if group_config["challenge_timeout_action"] == "ban":
            await client.ban_chat_member(chat_id, from_id)
        elif group_config["challenge_timeout_action"] == "kick":
            await client.ban_chat_member(chat_id, from_id)
            await client.unban_chat_member(chat_id, from_id)
        else:
            pass

        if group_config["delete_failed_challenge"]:
            Timer(
                client.delete_messages(chat_id, reply_id),
                group_config["delete_failed_challenge_interval"],
            )


def _main():
    global _app, _channel, _start_message, _config, _blacklist, _groups,_whitelist
    load_config()
    _start_message = _config["msg_start_message"]
    _proxy_ip = _config["proxy_addr"].strip()
    _proxy_port = _config["proxy_port"].strip()
    _blacklist = _config["blacklist"]
    _whitelist = _config["whitelist"]
    _groups = _config["groups"]
    if _proxy_ip and _proxy_port:
        _app = Client("bot",
                      bot_token=_token,
                      api_id=_api_id,
                      api_hash=_api_hash,
                      proxy=dict(hostname=_proxy_ip, port=int(_proxy_port)))
    else:
        _app = Client("bot",
                      bot_token=_token,
                      api_id=_api_id,
                      api_hash=_api_hash)
    try:
        _update(_app)
        _app.run()
    except KeyboardInterrupt:
        quit()
    except Exception as e:
        logging.error(e)
        _main()


if __name__ == "__main__":
    _main()
