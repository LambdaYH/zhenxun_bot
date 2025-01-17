from tortoise import fields

from services.db_context import Model


class OpenCasesUser(Model):

    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    user_qq = fields.BigIntField()
    """用户id"""
    group_id = fields.BigIntField()
    """群聊id"""
    total_count: int = fields.IntField(default=0)
    """总开启次数"""
    blue_count: int = fields.IntField(default=0)
    """蓝色"""
    blue_st_count: int = fields.IntField(default=0)
    """蓝色暗金"""
    purple_count: int = fields.IntField(default=0)
    """紫色"""
    purple_st_count: int = fields.IntField(default=0)
    """紫色暗金"""
    pink_count: int = fields.IntField(default=0)
    """粉色"""
    pink_st_count: int = fields.IntField(default=0)
    """粉色暗金"""
    red_count: int = fields.IntField(default=0)
    """紫色"""
    red_st_count: int = fields.IntField(default=0)
    """紫色暗金"""
    knife_count: int = fields.IntField(default=0)
    """金色"""
    knife_st_count: int = fields.IntField(default=0)
    """金色暗金"""
    spend_money: int = fields.IntField(default=0)
    """花费金币"""
    make_money: float = fields.FloatField(default=0)
    """赚取金币"""
    today_open_total: int = fields.IntField(default=0)
    """今日开箱数量"""
    open_cases_time_last = fields.DatetimeField()
    """最后开箱日期"""
    knifes_name: str = fields.TextField(default="")
    """已获取金色"""

    class Meta:
        table = "open_cases_users"
        table_description = "开箱统计数据表"
        unique_together = ("user_qq", "group_id")

    @classmethod
    async def _run_script(cls):
        await cls.raw(
            "alter table open_cases_users alter COLUMN make_money type float;"
        )
        """将make_money字段改为float"""
