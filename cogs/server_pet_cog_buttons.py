@commands.command(name="pet")
async def pet_command(self, ctx):
    view = View()
    for action in ACTION_VALUES:
        print(f"追加ボタン: {action}")  # ここでログを出す
        view.add_item(ActionButton(action, self.bot))
    await ctx.send("テスト用ペットコマンドです。", view=view)
