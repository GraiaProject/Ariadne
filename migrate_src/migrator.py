import argparse
import pathlib
from typing import Dict, Optional, Set

import rich

MAPPING: Dict[str, str] = {
    "messageChain": "message_chain",
    "durationSeconds": "duration",
    "messageId": "message_id",
    "authorId": "author_id",
    "requestId": "request_id",
    "sourceGroup": "source_group",
    "groupName": "group_name",
    "rejectAndBlock": "reject_and_block",
    "ignoreAndBlock": "ignore_and_block",
    "MessageChain.create": "MessageChain",
    "asSendable": "as_sendable",
    "buildChain": "build_chain",
    "downloadBinary": "download_binary",
    "findSubChain": "find_sub_chain",
    "getFirst": "get_first",
    "getOne": "get_one",
    "merge(copy=True)": "merge()",
    "onlyContains": "only",
    "get_running(Ariadne)": "Ariadne.current()",
    "deleteAnnouncement": "delete_announcement",
    "deleteFile": "delete_file",
    "deleteFriend": "delete_friend",
    "executeCommand": "execute_command",
    "getAnnouncementIterator": "get_announcement_iterator",
    "getAnnouncementList": "get_announcement_list",
    "getBotProfile": "get_bot_profile",
    "getFileInfo": "get_file_info",
    "getFileIterator": "get_file_iterator",
    "getFileList": "get_file_list",
    "getFriend": "get_friend",
    "getFriendList": "get_friend_list",
    "getFriendProfile": "get_friend_profile",
    "getGroup": "get_group",
    "getGroupConfig": "get_group_config",
    "getGroupList": "get_group_list",
    "getMember": "get_member",
    "getMemberList": "get_member_list",
    "getMemberProfile": "get_member_profile",
    "getMessageFromId": "get_message_from_id",
    "getUserProfile": "get_user_profile",
    "getVersion": "get_version",
    "kickMember": "kick_member",
    "makeDirectory": "make_directory",
    "modifyGroupConfig": "modify_group_config",
    "modifyMemberAdmin": "modify_member_admin",
    "modifyMemberInfo": "modify_member_info",
    "moveFile": "move_file",
    "muteAll": "mute_all",
    "muteMember": "mute_member",
    "publishAnnouncement": "publish_announcement",
    "quitGroup": "quit_group",
    "recallMessage": "recall_message",
    "registerCommand": "register_command",
    "renameFile": "rename_file",
    "sendFriendMessage": "send_friend_message",
    "sendGroupMessage": "send_group_message",
    "sendMessage": "send_message",
    "sendNudge": "send_nudge",
    "sendTempMessage": "send_temp_message",
    "setEssence": "set_essence",
    "unmuteAll": "unmute_all",
    "unmuteMember": "unmute_member",
    "uploadFile": "upload_file",
    "uploadImage": "upload_image",
    "uploadVoice": "upload_voice",
    "fetchOriginal": "fetch_original",
    "toFlashImage": "to_flash_image",
    "toImage": "to_image",
    "getBytes": "get_bytes",
    "asDisplay()": "display",
    "asPersistentString": "as_persistent_string",
    "fromPersistentString": "from_persistent_string",
    "asNoPersistentBinary()": "as_persistent_string(binary=False)",
}

WARNINGS: Set[str] = {"get_running", "Adapter", ".display"}

console = rich.console.Console()


def analyze_file(file: pathlib.Path):
    if file.name.endswith(".modified.py"):
        return
    original = file.read_text("utf-8")
    changed = original
    console.print(f"[blue]Analyzing {file}")
    for key, value in MAPPING.items():
        changed = changed.replace(key, value)
    for entry in WARNINGS:
        for line_cnt, line in enumerate(changed.split("\n"), 1):
            if entry in line:
                console.print(f"[red] Warning: found {entry} at {line_cnt}")
    modified = file.parent / f"{file.stem}.modified.py"
    modified.write_text(changed, "utf-8")


def analyze_dir(dir: pathlib.Path):
    console.print(f"[dark_orange]Analyzing {dir}")
    for file in dir.glob("*.py"):
        analyze_file(file)
    for dir in dir.glob("*"):
        if dir.is_dir():
            analyze_dir(dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="The target to be analyzed")
    parser.add_argument("-o", "--output", help="The log file")
    args = parser.parse_args()
    target: str = args.target
    output: Optional[str] = args.output
    if output:
        console = rich.console.Console(file=open(output, "w"))
    root_pth = pathlib.Path(target)
    if root_pth.is_dir():
        analyze_dir(root_pth)
    else:
        analyze_file(root_pth)
