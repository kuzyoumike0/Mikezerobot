    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.events:
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[emoji_str]

        # すでに登録済みかチェック（重複登録防止）
        if member.display_name not in event["reactions"][label]:
            event["reactions"][label].append(member.display_name)

        await self.update_embed(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self.events:
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[emoji_str]

        if member.display_name in event["reactions"][label]:
            event["reactions"][label].remove(member.display_name)

        await self.update_embed(payload.message_id)
