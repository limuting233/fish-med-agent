import argparse
import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fish_med_agent.core.security import hash_password
from fish_med_agent.db.engine import async_engine
from fish_med_agent.db.session import AsyncSessionLocal
from fish_med_agent.models import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="插入一个用户")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--password", help="密码；不传则交互输入")
    parser.add_argument("--nickname", help="昵称")
    parser.add_argument("--email", help="邮箱")
    parser.add_argument("--phone", help="手机号")
    parser.add_argument("--inactive", action="store_true", help="插入为禁用状态")
    return parser.parse_args()


def read_password(password: str | None) -> str:
    if password:
        return password

    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise ValueError("两次输入的密码不一致")
    if not first:
        raise ValueError("密码不能为空")
    return first


async def ensure_user_not_exists(
        *,
        username: str,
        email: str | None,
        phone: str | None,
) -> None:
    conditions = [User.username == username]
    if email:
        conditions.append(User.email == email)
    if phone:
        conditions.append(User.phone == phone)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(or_(*conditions)))
        exist_users = result.scalars().all()

    if not exist_users:
        return

    conflict_messages = []
    for exist_user in exist_users:
        if exist_user.username == username:
            conflict_messages.append(f"用户名已存在: {username}")
        if email and exist_user.email == email:
            conflict_messages.append(f"邮箱已存在: {email}")
        if phone and exist_user.phone == phone:
            conflict_messages.append(f"手机号已存在: {phone}")

    raise ValueError("; ".join(conflict_messages))


async def insert_user(args: argparse.Namespace) -> User:
    password = read_password(args.password)
    await ensure_user_not_exists(
        username=args.username,
        email=args.email,
        phone=args.phone,
    )

    user = User(
        username=args.username,
        password=hash_password(password),
        nickname=args.nickname,
        email=args.email,
        phone=args.phone,
        is_active=not args.inactive,
    )

    async with AsyncSessionLocal() as session:
        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("用户唯一字段冲突，请检查 username/email/phone") from exc


async def main() -> None:
    args = parse_args()
    try:
        user = await insert_user(args)
    finally:
        await async_engine.dispose()

    print(f"用户插入成功: id={user.id}, username={user.username}, is_active={user.is_active}")


if __name__ == "__main__":
    asyncio.run(main())
