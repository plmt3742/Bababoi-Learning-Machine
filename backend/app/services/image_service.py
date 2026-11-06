"""图片存储与预处理（05 §6.8 / ADR-004）。

三条刻意的取舍，都写在 05 里，这里只放实现理由：

1. **只存一份**：落库的是"EXIF 转正 + 剥元数据 + 长边 ≤2000px 的 JPEG"，
   手机原图（4000px+、带 GPS）只在内存里过一遍就不留了。代价是用户事后没法把裁剪范围
   改大（外围像素已不在库里），只能重选照片——这是有意的，不是 bug。
2. **`image_path` 是标识符不是文件系统路径**：库里存 `uploads/{user_id}/{name}`，
   真实位置由 `settings.upload_dir` 决定。这样把上传目录换到 /var/data/uploads 时，
   历史行仍然能读——直接把绝对路径写进库就死在这一步。
3. **文件名内容寻址**（sha256 前 16 位）：元数据剥干净之后"同图必同名"，天然去重，
   也因此 `GET /uploads/...` 才敢挂 `Cache-Control: immutable`。

不做的事：不挂 StaticFiles（那等于绕过鉴权暴露整个目录），不做文字方向识别
（拍反了前端上传前转一下就够，多打一次模型延迟成本都翻倍）。
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode

# 路径里的那一段永远是这个字面值，与 settings.upload_dir 的实际位置无关
PATH_PREFIX = "uploads"
# 文件名段的正则**不带锚点**单独存一份：把它塞进 IMAGE_PATH_RE 时如果连着 `^...$` 一起塞，
# Python 会把中间的 `^` 当成"必须是串首"，于是任何 image_path 都匹配不上（实测踩过）。
_FILENAME_PATTERN = r"[0-9a-f]{16}\.(?:jpg|png|webp)"
# 内容寻址名：16 位十六进制 + 三种允许的扩展名，不接受别的东西（顺带堵死路径穿越）
FILENAME_RE = re.compile(rf"^{_FILENAME_PATTERN}$")
IMAGE_PATH_RE = re.compile(rf"^{PATH_PREFIX}/(\d+)/({_FILENAME_PATTERN})$")

# Pillow 嗅出来的格式名 → 标准 media_type；哪些格式能进门由 settings.image_allowed_types 说
_PIL_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
# 落盘固定用 JPEG：输入哪怕是 PNG/WebP，出来都是带白底的 JPEG 单份文件
_STORED_MEDIA_TYPE = "image/jpeg"
_STORED_EXTENSION = "jpg"
_JPEG_QUALITY = 85
# 体积压不下去时的退让档位，到底还超就认输（这种图本来也不该往这传）
_QUALITY_FLOOR = 45


@dataclass(frozen=True)
class StoredImage:
    """上传成功后回给前端的东西；`url` 是带鉴权头的取图路径，不是公开直链。"""

    image_path: str
    url: str
    width: int
    height: int
    media_type: str


def _root() -> Path:
    return Path(settings.upload_dir).resolve()


def _dir_for(user_id: int) -> Path:
    return Path(settings.upload_dir) / str(user_id)


def _open(raw: bytes) -> Image.Image:
    """按字节嗅格式，不看客户端给的 MIME，也不看文件后缀。

    扩展名/jpg 但内容是别的，是真实存在的情况（前端拖拽、改名、脚本上传都会）。
    """
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Image.DecompressionBombError:
        # 像素数超了 Pillow 的默认上限（89,478,485）——按"图片超限"报，别让它变成 500
        raise ApiError(ErrorCode.UPLOAD_TOO_LARGE, "图片像素规模超出允许范围", 413) from None
    except Exception:  # noqa: BLE001  # 解不开就是不是图，原因不用往外抄
        raise ApiError(
            ErrorCode.UPLOAD_UNSUPPORTED_TYPE,
            "图片格式不支持或文件已损坏（只接受 JPEG/PNG/WebP）",
            415,
        ) from None
    media_type = _PIL_TO_MIME.get(image.format or "")
    if media_type not in settings.image_allowed_types:
        raise ApiError(
            ErrorCode.UPLOAD_UNSUPPORTED_TYPE,
            f"图片格式不支持（识别为 {image.format}，只接受 "
            f"{'/'.join(settings.image_allowed_types)}）",
            415,
        )
    return image


def _flatten(image: Image.Image) -> Image.Image:
    """EXIF 转正 + 统一成 RGB。

    `exif_transpose` 只处理手机竖拍那种 orientation 标记；读不到就当没标记按原样走，
    不值得为一段坏元数据把整张图判死。转 RGB 时带透明通道的 PNG 摊到白底上——
    摊到黑底上白字公式就没了。
    """
    try:
        transposed = ImageOps.exif_transpose(image)
    except Exception:  # noqa: BLE001
        transposed = None
    if transposed is not None:
        image = transposed
    if image.mode in {"RGBA", "LA", "P"}:
        background = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _fit_within(image: Image.Image, max_edge: int) -> Image.Image:
    if max(image.width, image.height) <= max_edge:
        return image
    scale = max_edge / max(image.width, image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _encode_within_limit(image: Image.Image, limit: int) -> tuple[bytes, int, int]:
    """先降到长边上限，再沿质量档退让（85→75→…→45），一边退一边看体积。

    返回的是**落盘那张的实际尺寸**，不是传进来那张的：前端按 width/height 占位防跳版，
    给成原图尺寸就会一开始就撑错比例。

    只降质量不缩尺寸对"高像素但内容简单"的图有效；反过来内容复杂的截图得靠缩尺寸。
    两条都试过还超，就是真的不该往这传。
    """
    sized = _fit_within(image, settings.image_max_edge_px)
    for quality in range(_JPEG_QUALITY, _QUALITY_FLOOR - 1, -10):
        buffer = io.BytesIO()
        sized.save(buffer, "JPEG", quality=quality, optimize=True)
        if buffer.tell() <= limit:
            return buffer.getvalue(), sized.width, sized.height
        if quality == _JPEG_QUALITY and sized.width > 400 and sized.height > 400:
            # 顶格质量还超就先缩一轮再回到质量循环，别一上来就把字压糊
            sized = _fit_within(sized, int(max(sized.width, sized.height) * 0.85))
    raise ApiError(
        ErrorCode.UPLOAD_TOO_LARGE,
        f"图片压到 {_QUALITY_FLOOR} 质量仍超过 {limit // (1024 * 1024)}MB",
        413,
    )


def store_upload(user_id: int, raw: bytes) -> StoredImage:
    """校验 → 转正 → 剥元数据 → 压缩 → 落盘，返回可以直接给前端的那份描述。"""
    if len(raw) > settings.image_max_upload_bytes:
        raise ApiError(
            ErrorCode.UPLOAD_TOO_LARGE,
            f"图片超过 {settings.image_max_upload_bytes // (1024 * 1024)}MB 上限",
            413,
        )
    image = _flatten(_open(raw))
    data, width, height = _encode_within_limit(image, settings.image_max_stored_bytes)
    name = f"{hashlib.sha256(data).hexdigest()[:16]}.{_STORED_EXTENSION}"

    directory = _dir_for(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    if not target.exists():
        # 内容寻址：同样的字节必然是同一个名字，已存在就是已存过，不必重写
        with open(target, "wb") as handle:
            handle.write(data)

    return StoredImage(
        image_path=f"{PATH_PREFIX}/{user_id}/{name}",
        url=f"{settings.api_prefix}/{PATH_PREFIX}/{user_id}/{name}",
        width=width,
        height=height,
        media_type=_STORED_MEDIA_TYPE,
    )


def resolve_stored(user_id: int, filename: str) -> Path:
    """按"文件名段"定位当前用户的那份图；任何不合形状的要求都当不存在。

    不合形状包含三种：文件名不是内容寻址名（顺带堵死 `..`、`/`、反斜杠），
    用户号不是本人，以及文件不在了。三种一律 404——403 等于告诉对方"这文件存在但不属于你"，
    那是泄露存在性（前端意见单 §一，我认同）。
    """
    if not FILENAME_RE.fullmatch(filename or ""):
        raise ApiError(ErrorCode.NOT_FOUND, "图片不存在", 404)
    path = _dir_for(user_id) / filename
    if not path.is_file():
        raise ApiError(ErrorCode.NOT_FOUND, "图片不存在", 404)
    return path


def resolve_user_file(user_id: int, image_path: str) -> Path:
    """按库里的 `image_path` 标识符定位文件；前缀与用户号都要对上。"""
    match = IMAGE_PATH_RE.match(image_path or "")
    if match is None or int(match.group(1)) != user_id:
        raise ApiError(ErrorCode.NOT_FOUND, "图片不存在", 404)
    return resolve_stored(user_id, match.group(2))


def read_for_download(user_id: int, filename: str) -> tuple[bytes, str]:
    """鉴权取图用。落盘只有 JPEG 一种，media_type 不需要按后缀猜。"""
    return resolve_stored(user_id, filename).read_bytes(), _STORED_MEDIA_TYPE


def data_url_for_llm(user_id: int, image_path: str) -> str:
    """送多模态模型前在内存里压到长边 ≤1200（14 号 §5-3），不落第二份文件。

    实测同一页教材：长边 1400 时 4 道题 19.9s / 884+3999 token、题型规则全通过；
    再大就是白花 token 和时间。
    """
    path = resolve_user_file(user_id, image_path)
    image = _fit_within(_flatten(Image.open(path)), settings.image_llm_max_edge_px)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=_JPEG_QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
