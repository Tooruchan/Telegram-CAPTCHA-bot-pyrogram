import asyncio
import json
import threading
from time import time, sleep
from challenge import Challenge
from pyrogram import (
    Client,
    Filters,
    Message,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from pyrogram.api.errors.exceptions import *

_app: Client = None
_channel: str = None
_start_message: str = None
# _challenge_scheduler = sched.scheduler(time, sleep)
_current_challenges = dict()
_cch_lock = threading.Lock()
_config = dict()


class _Timer:
    def __init__(self, callback, timeout):
        loop = asyncio.get_event_loop()
        self.callback = callback
        self.timeout = timeout
        self.task = loop.create_task(self.wait())

    async def wait(self):
        await asyncio.sleep(self.timeout)
        await self.callback

    def stop(self):
        try:
            self.task.cancel()
        except asyncio.CancelledError:
            pass


def load_config():
    global _config
    with open("config.json", encoding="utf-8") as f:
        _config = json.load(f)


def save_config():
    with open("config.json", "w") as f:
        json.dump(_config, f, indent=4)


def _update(app):
    @app.on_message(Filters.command("ping") & Filters.private)
    async def ping_command(client: Client, message: Message):
        await message.reply("poi~")

    @app.on_message(Filters.command("start") & Filters.private)
    async def start_command(client: Client, message: Message):
        await message.reply(_start_message)
    
    @app.on_message(Filters.command("leave") & Filters.private)
    async def leave_command(client: Client, message: Message):
        chat_id = message.text.split()[-1]
        if message.from_user.id == _config["manage_user"]:
            try:
                await client.send_message(int(chat_id),_config["msg_leave_msg"])
                await client.leave_chat(int(chat_id),True)
            except:
                await message.reply("指令出错了！可能是bot不在参数所在群里。")
            else:
                await message.reply("已离开群组: `"+chat_id+"`",parse_mode="Markdown")
                _me: User = await client.get_me()
                await client.send_message(
                    int(_channel),
                    _config["msg_leave_group"].format(
                        botid=str(_me.id),
                        groupid=chat_id,
                    ),
                    parse_mode="Markdown")
        else:
            pass

    @app.on_callback_query()
    async def challenge_callback(client: Client, callback_query: CallbackQuery):
        query_data = str(callback_query.data, encoding="utf-8")
        query_id = callback_query.id
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        msg_id = callback_query.message.message_id
        chat_title = callback_query.message.chat.title
        user_name = callback_query.from_user.first_name
        group_config = _config.get(str(chat_id), _config["*"])
        if query_data in ["+", "-"]:
            admins = await client.get_chat_members(chat_id, filter="administrators")
            if not any(
                [
                    admin.user.id == user_id
                    and (admin.can_restrict_members or admin.status == "creator")
                    for admin in admins.chat_members
                ]
            ):
                await client.answer_callback_query(
                    query_id, group_config["msg_permission_denied"]
                )
                return

            ch_id = "{chat}|{msg}".format(chat=chat_id, msg=msg_id)
            _cch_lock.acquire()
            # target: int = None
            challenge, target, timeout_event = _current_challenges.get(
                ch_id, (None, None, None)
            )
            del _current_challenges[ch_id]
            _cch_lock.release()
            timeout_event.stop()

            if query_data == "+":
                try:
                    await client.restrict_chat_member(
                        chat_id,
                        target,
                        can_send_other_messages=True,
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_add_web_page_previews=True,
                    )
                except ChatAdminRequired:
                    await client.answer_callback_query(
                        query_id, group_config["msg_bot_no_permission"]
                    )
                    return

                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_approved"].format(user=user_name),
                    reply_markup=None,
                )
                _me: User = await client.get_me()
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
            else:
                try:
                    await client.kick_chat_member(chat_id, target)
                except ChatAdminRequired:
                    await client.answer_callback_query(
                        query_id, group_config["msg_bot_no_permission"]
                    )
                    return
                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_refused"].format(user=user_name),
                    reply_markup=None,
                )
                _me: User = await client.get_me()
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
            await client.answer_callback_query(query_id)
            return

        ch_id = "{chat}|{msg}".format(chat=chat_id, msg=msg_id)
        _cch_lock.acquire()
        challenge, target, timeout_event = _current_challenges.get(
            ch_id, (None, None, None)
        )
        _cch_lock.release()
        if user_id != target:
            await client.answer_callback_query(
                query_id, group_config["msg_challenge_not_for_you"]
            )
            return None
        timeout_event.stop()
        try:
            await client.restrict_chat_member(
                chat_id,
                target,
                can_send_other_messages=True,
                can_send_messages=True,
                can_send_media_messages=True,
                can_add_web_page_previews=True,
            )
        except ChatAdminRequired:
            pass

        correct = str(challenge.ans()) == query_data
        if correct:
            await client.edit_message_text(
                chat_id, msg_id, group_config["msg_challenge_passed"], reply_markup=None
            )
            _me: User = await client.get_me()
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
        else:
            if not group_config["use_strict_mode"]:
                await client.edit_message_text(
                    chat_id,
                    msg_id,
                    group_config["msg_challenge_mercy_passed"],
                    reply_markup=None,
                )
                _me: User = await client.get_me()
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
            else:
                try:
                    await client.edit_message_text(
                        chat_id,
                        msg_id,
                        group_config["msg_challenge_failed"],
                        reply_markup=None,
                    )
                    await client.restrict_chat_member(chat_id, target)
                    _me: User = await client.get_me()
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
                except ChatAdminRequired:
                    return

                if group_config["challenge_timeout_action"] == "ban":
                    await client.kick_chat_member(chat_id, user_id)
                elif group_config["challenge_timeout_action"] == "kick":
                    await client.kick_chat_member(chat_id, user_id)
                    await client.unban_chat_member(chat_id, user_id)
                else:
                    pass

                if group_config["delete_failed_challenge"]:
                    _Timer(
                        client.delete_messages(chat_id, msg_id),
                        group_config["delete_failed_challenge_interval"],
                    )
        if group_config["delete_passed_challenge"]:
            _Timer(
                client.delete_messages(chat_id, msg_id),
                group_config["delete_passed_challenge_interval"],
            )

    @app.on_message(Filters.new_chat_members)
    async def challenge_user(client: Client, message: Message):
        target = message.new_chat_members[0]
        if message.from_user.id != target.id:
            if target.is_self:
                group_config = _config.get(str(message.chat.id), _config["*"])
                try:
                    await client.send_message(
                        message.chat.id, group_config["msg_self_introduction"]
                    )
                    _me: User = await client.get_me()
                    await client.send_message(
                        int(_channel),
                        _config["msg_into_group"].format(
                            botid=str(_me.id),
                            groupid=str(message.chat.id),
                            grouptitle=str(message.chat.title),
                        ),
                        parse_mode="Markdown",
                    )
                except ChannelPrivate:
                    return
            return
        try:
            await client.restrict_chat_member(
                chat_id=message.chat.id, user_id=target.id
            )
        except ChatAdminRequired:
            return
        group_config = _config.get(str(message.chat.id), _config["*"])
        challenge = Challenge()

        def generate_challenge_button(e):
            choices = [
                [
                    InlineKeyboardButton(
                        str(c), callback_data=bytes(str(c), encoding="utf-8")
                    )
                ]
                for c in e.choices()
            ]
            return choices + [
                [
                    InlineKeyboardButton(
                        group_config["msg_approve_manually"], callback_data=b"+"
                    ),
                    InlineKeyboardButton(
                        group_config["msg_refuse_manually"], callback_data=b"-"
                    ),
                ]
            ]

        timeout = group_config["challenge_timeout"]
        reply_message = await client.send_message(
            message.chat.id,
            group_config["msg_challenge"].format(
                timeout=timeout, challenge=challenge.qus()
            ),
            reply_to_message_id=message.message_id,
            reply_markup=InlineKeyboardMarkup(generate_challenge_button(challenge)),
        )

        timeout_event = _Timer(
            challenge_timeout(
                client, message.chat.id, message.from_user.id, reply_message.message_id
            ),
            timeout=group_config["challenge_timeout"],
        )
        _cch_lock.acquire()
        _current_challenges[
            "{chat}|{msg}".format(chat=message.chat.id, msg=reply_message.message_id)
        ] = (challenge, message.from_user.id, timeout_event)
        _cch_lock.release()

    async def challenge_timeout(client: Client, chat_id, from_id, reply_id):
        global _current_challenges
        group_config = _config.get(str(chat_id), _config["*"])

        _cch_lock.acquire()
        del _current_challenges["{chat}|{msg}".format(chat=chat_id, msg=reply_id)]
        _cch_lock.release()

        # TODO try catch
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=reply_id,
            text=group_config["msg_challenge_failed"],
            reply_markup=None,
        )

        if group_config["challenge_timeout_action"] == "ban":
            await client.kick_chat_member(chat_id, from_id)
        elif group_config["challenge_timeout_action"] == "kick":
            await client.kick_chat_member(chat_id, from_id)
            await client.unban_chat_member(chat_id, from_id)
        else:
            pass

        if group_config["delete_failed_challenge"]:
            _Timer(
                client.delete_messages(chat_id, reply_id),
                group_config["delete_failed_challenge_interval"],
            )


def _main():
    global _app, _channel, _start_message
    load_config()
    _api_id = _config["api_id"]
    _api_hash = _config["api_hash"]
    _token = _config["token"]
    _channel = _config["channel"]
    _start_message = _config["msg_start_message"]
    _app = Client(_token, api_id=_api_id, api_hash=_api_hash)
    _update(_app)
    _app.run()


if __name__ == "__main__":
    _main()
