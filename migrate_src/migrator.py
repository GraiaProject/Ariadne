import argparse
import difflib
import pathlib
import shutil
from typing import Dict, Literal, Optional, Set

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
    "get_running()": "Ariadne.current()",
    "get_running(Ariadne)": "Ariadne.current()",
    "get_running(Broadcast)": "Ariadne.broadcast",
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
    "getGroupList": "get_group_list",
    "getGroupConfig": "get_group_config",
    "getGroup": "get_group",
    "getMemberList": "get_member_list",
    "getMemberProfile": "get_member_profile",
    "getMessageFromId": "get_message_from_id",
    "getUserProfile": "get_user_profile",
    "getMember": "get_member",
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

WARNINGS: Set[str] = {"get_running", "Adapter"}

console = rich.console.Console()

mode: Literal["copy", "diff", "modify"] = "copy"


def analyze_file(file: pathlib.Path):
    if file.name.endswith(".modified.py"):
        return
    modified = file.parent / f"{file.stem}.modified.py"
    origin = text = file.read_text("utf-8")
    console.print(f"[blue]Analyzing {file}")
    for key, value in MAPPING.items():
        text = text.replace(key, value)
    diff = "\n".join(
        difflib.unified_diff(origin.splitlines(), text.splitlines(), fromfile=file.name, tofile=modified.name)
    )
    if mode == "diff":
        diff_pth = file.parent / f"{file.stem}.diff"
        diff_pth.touch()
        diff_pth.write_text(diff, "utf-8")
        return
    if mode == "modify":
        modified.write_text(text, "utf-8")
    else:
        file.write_text(text, "utf-8")
    console.print(diff)


def analyze_dir(dir: pathlib.Path):
    console.print(f"[dark_orange]Analyzing {dir}")
    for file in dir.glob("*.py"):
        analyze_file(file)
    for dir in dir.glob("*"):
        if dir.is_dir() and not dir.parts[-1].startswith("."):
            analyze_dir(dir)


# TODO: a mode of copying everything to a new directory and modify in-place

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="分析目标，文件夹或 .py 文件")
    parser.add_argument("-o", "--output", help="日志文件存放位置, 否则直接打印到控制台")
    parser.add_argument(
        "-m",
        "--mode",
        default="copy",
        choices=["copy", "diff", "modify"],
        help="copy: 复制到新文件夹后原地修改, diff: 只输出 diff, modify: 在本地输出 .modified.py",
    )
    args = parser.parse_args()
    target: str = args.target
    output: Optional[str] = args.output
    if output:
        console = rich.console.Console(file=open(output, "w"))
    mode = args.mode
    root_pth = pathlib.Path(target).absolute()
    if root_pth.is_dir():
        if mode == "copy":
            cp_path = root_pth.parent / f"{root_pth.parts[-1]}_modified"
            cp_path.mkdir(exist_ok=True)
            shutil.copytree(root_pth, cp_path, dirs_exist_ok=True)
            root_pth = cp_path
        analyze_dir(root_pth)
    else:
        if mode == "copy":
            mode = "modify"
        analyze_file(root_pth)
