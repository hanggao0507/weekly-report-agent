from __future__ import annotations

import json

from src.config.settings import Settings
from src.models import MemberProfile, NormalizedWorkItem


class MemberDirectory:
    def __init__(self, settings: Settings):
        path = settings.resolve_path(settings.team.members_file)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.members = [MemberProfile(**item) for item in payload]
        self.by_id = {member.member_id: member for member in self.members}

    def all(self) -> list[MemberProfile]:
        return list(self.members)

    def assign_member(self, item: NormalizedWorkItem) -> str | None:
        raw = item.raw
        if item.source == "github":
            login = raw.get("author_login")
            email = raw.get("author_email")
            for member in self.members:
                if login in member.github_logins:
                    return member.member_id
            for member in self.members:
                if email in member.github_emails:
                    return member.member_id
            title = item.title.lower()
            for member in self.members:
                if any(alias.lower() in title for alias in member.aliases):
                    return member.member_id
            return None

        if item.source == "feishu":
            user_id = raw.get("owner_user_id") or raw.get("sender_user_id")
            name = (raw.get("owner_name") or raw.get("sender_name") or "").lower()
            for member in self.members:
                if user_id and user_id == member.feishu_user_id:
                    return member.member_id
            for member in self.members:
                aliases = {member.display_name.lower(), *[alias.lower() for alias in member.aliases]}
                if name and name in aliases:
                    return member.member_id
            return None

        return None

