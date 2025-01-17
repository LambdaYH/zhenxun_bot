import asyncio
import random
from datetime import datetime
from typing import Union

import pypinyin
from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from configs.config import Config
from configs.path_config import IMAGE_PATH
from models.sign_group_user import SignGroupUser
from services.log import logger
from utils.image_utils import BuildImage, alpha2white_pil
from utils.message_builder import image
from utils.utils import cn2py

from .config import *
from .models.buff_prices import BuffPrice
from .models.open_cases_user import OpenCasesUser

RESULT_MESSAGE = {
    "BLUE": ["这样看着才舒服", "是自己人，大伙把刀收好", "非常舒适~"],
    "PURPLE": ["还行吧，勉强接受一下下", "居然不是蓝色，太假了", "运气-1-1-1-1-1..."],
    "PINK": ["开始不适....", "你妈妈买菜必涨价！涨三倍！", "你最近不适合出门，真的"],
    "RED": ["已经非常不适", "好兄弟你开的什么箱子啊，一般箱子不是只有蓝色的吗", "开始拿阳寿开箱子了？"],
    "KNIFE": ["你的好运我收到了，你可以去喂鲨鱼了", "最近该吃啥就迟点啥吧，哎，好好的一个人怎么就....哎", "众所周知，欧皇寿命极短."],
}

COLOR2NAME = {"BLUE": "军规", "PURPLE": "受限", "PINK": "保密", "RED": "隐秘", "KNIFE": "罕见"}

COLOR2CN = {"BLUE": "蓝", "PURPLE": "紫", "PINK": "粉", "RED": "红", "KNIFE": "金"}


def add_count(user: OpenCasesUser, skin: BuffSkin):
    if skin.color == "BLUE":
        if skin.is_stattrak:
            user.blue_st_count += 1
        else:
            user.blue_count += 1
    elif skin.color == "PURPLE":
        if skin.is_stattrak:
            user.purple_st_count += 1
        else:
            user.purple_count += 1
    elif skin.color == "PINK":
        if skin.is_stattrak:
            user.pink_st_count += 1
        else:
            user.pink_count += 1
    elif skin.color == "RED":
        if skin.is_stattrak:
            user.red_st_count += 1
        else:
            user.red_count += 1
    elif skin.color == "KNIFE":
        if skin.is_stattrak:
            user.knife_st_count += 1
        else:
            user.knife_count += 1
    user.today_open_total += 1
    user.total_count += 1
    user.make_money += skin.skin_price
    user.spend_money += 17


async def get_user_max_count(user_qq: int, group_id: int) -> int:
    """获取用户每日最大开箱次数

    Args:
        user_qq (int): 用户id
        group_id (int): 群号

    Returns:
        int: 最大开箱次数
    """
    user, _ = await SignGroupUser.get_or_create(user_qq=user_qq, group_id=group_id)
    impression = int(user.impression)
    initial_open_case_count = Config.get_config("open_cases", "INITIAL_OPEN_CASE_COUNT")
    each_impression_add_count = Config.get_config(
        "open_cases", "EACH_IMPRESSION_ADD_COUNT"
    )
    return int(initial_open_case_count + impression / each_impression_add_count)  # type: ignore


async def open_case(
    user_qq: int, group_id: int, case_name: str = "狂牙大行动"
) -> Union[str, Message]:
    """开箱

    Args:
        user_qq (int): 用户id
        group_id (int): 群号
        case_name (str, optional): 武器箱名称. Defaults to "狂牙大行动".

    Returns:
        Union[str, Message]: 回复消息
    """
    if case_name not in ["狂牙大行动", "突围大行动", "命悬一线", "裂空", "光谱"]:
        return "武器箱未收录"
    logger.debug(f"尝试开启武器箱: {case_name}", "开箱", user_qq, group_id)
    case = cn2py(case_name)
    user = await OpenCasesUser.get_or_none(user_qq=user_qq, group_id=group_id)
    if not user:
        user = await OpenCasesUser.create(
            user_qq=user_qq, group_id=group_id, open_cases_time_last=datetime.now()
        )
    max_count = await get_user_max_count(user_qq, group_id)
    # 一天次数上限
    if user.today_open_total >= max_count:
        return _handle_is_MAX_COUNT()
    skin_list = await random_skin(1, case_name)
    if not skin_list:
        return "未抽取到任何皮肤..."
    skin, rand = skin_list[0]
    rand = str(rand)[:11]
    add_count(user, skin)
    ridicule_result = random.choice(RESULT_MESSAGE[skin.color])
    price_result = skin.skin_price
    if skin.color == "KNIFE":
        user.knifes_name = (
            user.knifes_name
            + f"{case}||{skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion}) 磨损：{rand}， 价格：{skin.skin_price},"
        )
    img_path = (
        IMAGE_PATH
        / "cases"
        / case
        / f"{cn2py(skin.name)} - {cn2py(skin.skin_name)}.png"
    )
    logger.info(
        f"开启{case_name}武器箱获得 {skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion}) 磨损: [{rand}] 价格: {skin.skin_price}",
        "开箱",
        user_qq,
        group_id,
    )
    await user.save()
    over_count = max_count - user.today_open_total
    return (
        f"开启{case_name}武器箱.\n剩余开箱次数:{over_count}.\n"
        + image(img_path)
        + "\n"
        + f"皮肤:[{COLOR2NAME[skin.color]}]{skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion})\n"
        f"磨损:{rand}\n"
        f"价格:{price_result}\n"
        f":{ridicule_result}"
    )


async def open_multiple_case(
    user_qq: int, group_id: int, case_name: str, num: int = 10
):
    user, _ = await OpenCasesUser.get_or_create(user_qq=user_qq, group_id=group_id)
    max_count = await get_user_max_count(user_qq, group_id)
    if user.today_open_total >= max_count:
        return _handle_is_MAX_COUNT()
    if max_count - user.today_open_total < num:
        return (
            f"今天开箱次数不足{num}次噢，请单抽试试看（也许单抽运气更好？）"
            f"\n剩余开箱次数:{max_count - user.today_open_total}"
        )
    if num < 5:
        h = 270
    elif num % 5 == 0:
        h = 270 * int(num / 5)
    else:
        h = 270 * int(num / 5) + 270
    case = cn2py(case_name)
    skin_count = {}
    img_list = []
    skin_list = await random_skin(num, case_name)
    if not skin_list:
        return "未抽取到任何皮肤..."
    total_price = 0
    for skin, rand in skin_list:
        total_price += skin.skin_price
        rand = str(rand)[:11]
        add_count(user, skin)
        color_name = COLOR2CN[skin.color]
        if skin.is_stattrak:
            color_name += "(暗金)"
        if not skin_count.get(color_name):
            skin_count[color_name] = 0
        skin_count[color_name] += 1
        if skin.color == "KNIFE":
            user.knifes_name = (
                user.knifes_name
                + f"{case}||{skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion}) 磨损：{rand}， 价格：{skin.skin_price},"
            )
        wImg = BuildImage(200, 270, 200, 200)
        await wImg.apaste(
            alpha2white_pil(
                Image.open(
                    IMAGE_PATH
                    / "cases"
                    / case
                    / f"{cn2py(skin.name)} - {cn2py(skin.skin_name)}.png"
                ).resize((200, 200), Image.ANTIALIAS)
            ),
            (0, 0),
        )
        await wImg.atext(
            (5, 200),
            f"{skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion})",
        )
        await wImg.atext((5, 220), f"磨损：{rand}")
        await wImg.atext((5, 240), f"价格：{skin.skin_price}")
        img_list.append(wImg)
        logger.info(
            f"开启{case_name}武器箱获得 {skin.name}{'（StatTrak™）' if skin.is_stattrak else ''} | {skin.skin_name} ({skin.abrasion}) 磨损: [{rand}] 价格: {skin.skin_price}",
            "开箱",
            user_qq,
            group_id,
        )
    await user.save()
    markImg = BuildImage(1000, h, 200, 270)
    for img in img_list:
        markImg.paste(img)
    over_count = max_count - user.today_open_total
    result = ""
    for color_name in skin_count:
        result += f"[{color_name}:{skin_count[color_name]}] "
    return (
        f"开启{case_name}武器箱\n剩余开箱次数：{over_count}\n"
        + image(markImg.pic2bs4())
        + "\n"
        + result[:-1]
        + f"\n总获取金额：{total_price:.2f}\n总花费：{17 * num}"
    )


def _handle_is_MAX_COUNT() -> str:
    return f"今天已达开箱上限了喔，明天再来吧\n(提升好感度可以增加每日开箱数 #疯狂暗示)"


async def total_open_statistics(user_qq: int, group: int) -> str:
    user, _ = await OpenCasesUser.get_or_create(user_qq=user_qq, group_id=group)
    return (
        f"开箱总数：{user.total_count}\n"
        f"今日开箱：{user.today_open_total}\n"
        f"蓝色军规：{user.blue_count}\n"
        f"蓝色暗金：{user.blue_st_count}\n"
        f"紫色受限：{user.purple_count}\n"
        f"紫色暗金：{user.purple_st_count}\n"
        f"粉色保密：{user.pink_count}\n"
        f"粉色暗金：{user.pink_st_count}\n"
        f"红色隐秘：{user.red_count}\n"
        f"红色暗金：{user.red_st_count}\n"
        f"金色罕见：{user.knife_count}\n"
        f"金色暗金：{user.knife_st_count}\n"
        f"花费金额：{user.spend_money}\n"
        f"获取金额：{user.make_money:.2f}\n"
        f"最后开箱日期：{user.open_cases_time_last.date()}"
    )


async def group_statistics(group: int):
    user_list = await OpenCasesUser.filter(group_id=group).all()
    #          lan   zi   fen   hong   jin  pricei
    uplist = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0]
    for user in user_list:
        uplist[0] += user.blue_count
        uplist[1] += user.blue_st_count
        uplist[2] += user.purple_count
        uplist[3] += user.purple_st_count
        uplist[4] += user.pink_count
        uplist[5] += user.pink_st_count
        uplist[6] += user.red_count
        uplist[7] += user.red_st_count
        uplist[8] += user.knife_count
        uplist[9] += user.knife_st_count
        uplist[10] += user.make_money
        uplist[11] += user.total_count
        uplist[12] += user.today_open_total
    return (
        f"群开箱总数：{uplist[11]}\n"
        f"群今日开箱：{uplist[12]}\n"
        f"蓝色军规：{uplist[0]}\n"
        f"蓝色暗金：{uplist[1]}\n"
        f"紫色受限：{uplist[2]}\n"
        f"紫色暗金：{uplist[3]}\n"
        f"粉色保密：{uplist[4]}\n"
        f"粉色暗金：{uplist[5]}\n"
        f"红色隐秘：{uplist[6]}\n"
        f"红色暗金：{uplist[7]}\n"
        f"金色罕见：{uplist[8]}\n"
        f"金色暗金：{uplist[9]}\n"
        f"花费金额：{uplist[11] * 17}\n"
        f"获取金额：{uplist[10]:.2f}"
    )


async def my_knifes_name(user_id: int, group: int):
    user, _ = await OpenCasesUser.get_or_create(user_qq=user_id, group_id=group)
    knifes_name = user.knifes_name
    if knifes_name:
        knifes_list = knifes_name[:-1].split(",")
        length = len(knifes_list)
        if length < 5:
            h = 600
            w = length * 540
        elif length % 5 == 0:
            h = 600 * int(length / 5)
            w = 540 * 5
        else:
            h = 600 * int(length / 5) + 600
            w = 540 * 5
        A = await asyncio.get_event_loop().run_in_executor(
            None, _pst_my_knife, w, h, knifes_list
        )
        return image(b64=A.pic2bs4())
    else:
        return "您木有开出金色级别的皮肤喔"


def _pst_my_knife(w, h, knifes_list):
    A = BuildImage(w, h, 540, 600)
    for knife in knifes_list:
        case = knife.split("||")[0]
        knife = knife.split("||")[1]
        name = knife[: knife.find("(")].strip()
        itype = knife[knife.find("(") + 1 : knife.find(")")].strip()
        mosun = knife[knife.find("磨损：") + 3 : knife.rfind("价格：")].strip()
        if mosun[-1] == "," or mosun[-1] == "，":
            mosun = mosun[:-1]
        price = knife[knife.find("价格：") + 3 :]
        skin_name = ""
        for i in pypinyin.pinyin(
            name.replace("|", "-").replace("（StatTrak™）", "").strip(),
            style=pypinyin.NORMAL,
        ):
            skin_name += "".join(i)
        knife_img = BuildImage(470, 600, 470, 470, font_size=20)
        knife_img.paste(
            alpha2white_pil(
                Image.open(IMAGE_PATH / f"cases" / case / f"{skin_name}.png").resize(
                    (470, 470), Image.ANTIALIAS
                )
            ),
            (0, 0),
        )
        knife_img.text((5, 500), f"\t{name}({itype})")
        knife_img.text((5, 530), f"\t磨损：{mosun}")
        knife_img.text((5, 560), f"\t价格：{price}")
        A.paste(knife_img)
    return A


# G3SG1（StatTrak™） |  血腥迷彩 (战痕累累)
# G3SG1（StatTrak™） | 血腥迷彩 (战痕累累)
# G3SG1（StatTrak™） | 血腥迷彩 (战痕累累)
