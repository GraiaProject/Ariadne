from graia.ariadne.model import Friend, Group, Member, MemberPerm
from graia.ariadne.util.permission import PermissionManager

if __name__ == "__main__":
    grp = Group(id=1, name="test", permission=MemberPerm.Member)
    friend_admin = Friend(id=2, nickname="admin", remark="admin")
    friend_member = Friend(id=3, nickname="member", remark="member")
    mgr = PermissionManager()
    mgr.set("", 0)
    mgr.set("", 1, friend_admin)  # set admin's everything to 1
    mgr.set("", 1, "group")  # allow group base access
    mgr.set("error", 0, friend_admin)
    mgr.set("app", 1)  # allow everone to use app
    print(mgr.get("app", friend_member))
    print(mgr.get("app", friend_admin))
    print(mgr.get("error", friend_admin))
    print(mgr.get("something", friend_admin))
    print(mgr.get("error.sth", friend_admin))
    print(mgr.get("app", grp))
    print(mgr.get("", friend_member))
    print(mgr.get("", friend_admin))
    print(mgr.get("", grp))
