"""Bilingual field checks for features visible in a crop photo, independent of diagnosis labels."""
from dataclasses import dataclass


VEGETABLE_GUIDE = 'https://apps.extension.umn.edu/garden/diagnose/plant/vegetable/'
DISEASE_GUIDE = 'https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/'
BOTH = ('potato', 'tomato')


@dataclass(frozen=True)
class Pattern:
    crops: tuple[str, ...]
    part: str
    # At least one complete group of visual features must be present.
    combinations: tuple[tuple[str, ...], ...]
    source: str
    en: tuple[str, str]
    bn: tuple[str, str]


PATTERNS = (
    Pattern(BOTH, 'leaf',
            (('collapsed_brown_leaflets', 'dark_stem_lesion'),
             ('collapsed_brown_leaflets', 'irregular_brown_leaf_blotches')),
            DISEASE_GUIDE + 'late-blight',
            ('Late blight is one possible cause of this pattern of brown, collapsed leaves. Other leaf or stem injuries can look similar.',
             'Photograph the underside at the edge of a fresh brown patch and the affected stem. If new patches are appearing, show the photos to a local agricultural extension officer promptly.'),
            ('বাদামি হয়ে পাতা নেতিয়ে পড়ার একটি সম্ভাব্য কারণ নাবি ধসা রোগ। পাতা বা কাণ্ডে অন্য ধরনের ক্ষতিতেও এমন হতে পারে।',
             'নতুন বাদামি দাগের কিনারায় পাতার নিচের পিঠ আর আক্রান্ত কাণ্ডের ছবি তুলুন। নতুন দাগ দেখা দিতে থাকলে দ্রুত স্থানীয় কৃষি কর্মকর্তাকে ছবিগুলো দেখান।')),
    Pattern(BOTH, 'leaf', (('round_brown_leaf_spots', 'rings_inside_leaf_spots'),),
            DISEASE_GUIDE + 'early-blight-in-tomato-and-potato',
            ('Brown spots with rings inside can occur with early blight.',
             'Photograph one spot in focus. Check whether older leaves near the ground have the same rings.'),
            ('বাদামি গোল দাগের ভেতরে একাধিক বলয় থাকলে আগাম ধসা রোগের সম্ভাবনা থাকে।',
             'একটি দাগের স্পষ্ট ছবি তুলুন। মাটির কাছের পুরোনো পাতাতেও এমন বলয় আছে কি না দেখুন।')),
    Pattern(('tomato',), 'leaf', (('upper_yellow_patches', 'olive_underside_growth'),),
            DISEASE_GUIDE + 'tomato-leaf-mold',
            ('Yellow patches with olive-colored growth underneath can fit tomato leaf mold.',
             'Photograph both faces of the same leaf and check whether the patches line up.'),
            ('পাতার ওপরে হলুদ দাগ আর নিচে জলপাই রঙের আবরণ টমেটোর পাতার ছাঁচ রোগে দেখা যেতে পারে।',
             'একই পাতার দুই পিঠের ছবি তুলে দেখুন, দাগগুলো একই জায়গায় আছে কি না।')),
    Pattern(('tomato',), 'leaf', (('pale_centered_leaf_spots', 'black_pinpoints_in_leaf_spots'),),
            VEGETABLE_GUIDE + 'tomato/leavesspots.html',
            ('Small spots with pale centers and black pinpoints inside can fit Septoria leaf spot.',
             'Take a close-up of several spots on an older leaf so the centers are visible.'),
            ('হালকা রঙের ছোট দাগের মাঝখানে কালো বিন্দু থাকলে সেপ্টোরিয়া পাতার দাগ রোগ হতে পারে।',
             'পুরোনো পাতার কয়েকটি দাগের কাছ থেকে ছবি তুলুন, যাতে দাগের মাঝের অংশ স্পষ্ট দেখা যায়।')),
    Pattern(('potato',), 'produce', (('rough_corky_tuber_patches', 'raised_or_pitted_tuber_skin'),),
            VEGETABLE_GUIDE + 'potato/tuberdiscoloredskin.html',
            ('Rough, raised or pitted patches on the potato skin can fit common scab. Other scab-like damage can resemble it.',
             'Photograph the skin in side light and check other tubers from the same harvest for similar patches.'),
            ('আলুর খোসায় খসখসে উঁচু দাগ বা ছোট গর্ত সাধারণ দাদ রোগের (কমন স্ক্যাব) সঙ্গে মেলে। অন্য ধরনের ক্ষতও দেখতে এমন হতে পারে।',
             'পাশ থেকে আলো ফেলে খোসার ছবি তুলুন। একই সময়ে তোলা অন্য আলুতেও এমন দাগ আছে কি না দেখুন।')),
    Pattern(('potato',), 'produce', (('sunken_tuber_patches', 'wrinkled_rings_on_tuber'),),
            VEGETABLE_GUIDE + 'potato/tuberholes.html',
            ('A sunken area with wrinkled rings on a tuber can fit dry rot. A surface photo leaves the cause uncertain.',
             'Photograph the edge of the sunken patch and check whether other stored tubers have the same wrinkles.'),
            ('আলুর বসে যাওয়া দাগের চারদিকে বলয়ের মতো ভাঁজ শুকনো পচা রোগের সঙ্গে মেলে। শুধু ওপরের ছবি দেখে কারণ নিশ্চিত করা কঠিন।',
             'বসে যাওয়া দাগের কিনারার ছবি তুলুন। সংরক্ষিত অন্য আলুতেও এমন ভাঁজ আছে কি না দেখুন।')),
    Pattern(('tomato',), 'produce', (('lesion_at_blossom_end', 'dark_sunken_fruit_tissue'),),
            VEGETABLE_GUIDE + 'tomato/fruitspots.html',
            ('A dark sunken area at the end opposite the stalk can fit blossom-end rot, a disorder that develops as the fruit grows.',
             'Photograph the stalk and opposite end of another affected tomato to show where the damage starts.'),
            ('টমেটোর বোঁটার উল্টো দিকে কালচে বসে যাওয়া দাগ ফলের নিচের অংশ পচা সমস্যার (ব্লসম-এন্ড রট) সঙ্গে মেলে। ফল বড় হওয়ার সময় এই সমস্যা দেখা দিতে পারে।',
             'আক্রান্ত আরেকটি টমেটোর বোঁটা আর বিপরীত প্রান্তের ছবি তুলুন, যাতে ক্ষতের অবস্থান বোঝা যায়।')),
    Pattern(('tomato',), 'produce', (('round_sunken_ripe_fruit_spots', 'dark_centers_in_fruit_spots'),),
            VEGETABLE_GUIDE + 'tomato/fruitspots.html',
            ('Round depressions with dark centers on a ripe tomato can fit anthracnose. Other fruit rots can overlap in appearance.',
             'Photograph the center and edge of a spot. Compare the marks on ripe and green fruit from the same plant.'),
            ('পাকা টমেটোয় মাঝখান কালচে এমন গোল বসে যাওয়া দাগ অ্যানথ্রাকনোজ রোগের সঙ্গে মেলে। অন্য পচা রোগেও এমন দাগ দেখা যায়।',
             'দাগের মাঝখান ও কিনারার ছবি তুলুন। একই গাছের পাকা আর কাঁচা ফলে দাগের ধরন মিলিয়ে দেখুন।')),
)


def visual_guidance(crop: str, part: str) -> str:
    """Only ask for visible features relevant to the selected crop and camera mode."""
    parts = {'auto': {'leaf', 'produce'}, 'leaf': {'leaf'}, 'other': {'produce'}}
    cues = sorted({cue for pattern in PATTERNS if crop in pattern.crops and pattern.part in parts.get(part, ())
                   for group in pattern.combinations for cue in group})
    if not cues:
        return ''
    return (
        '\n\nWhen visible, report these features in optional visible_features as an array of exact English identifiers: '
        + ', '.join(cues) + '. Report only features you can point to in the image and describe in signs. '
        'For multiple photos require the same crop and compatible findings. Use [] when unclear. '
        'Dark stem lesion means a localized damaged area, not a uniformly purple stem or a shadow. '
        'Brown collapsed leaflets means the affected leaflets are both brown and visibly drooping or shriveled. '
        'A whole plant with visible leaf damage can be part leaf. Keep assessing other visible patterns '
        'even when none of these features apply.'
    )


def field_check(crop: str, assessment: dict, locale: str) -> dict | None:
    """Return an extension reference for a compatible pattern without changing the recorded outcome."""
    if (assessment.get('crop_match') != 'match' or
            assessment.get('outcome') not in ('uncertain', 'possible_condition')):
        return None
    # Keep an existing specific, supported leaf finding and its own follow-up.
    if (assessment.get('part') == 'leaf' and assessment.get('condition') and
            assessment.get('distinguishing_sign')):
        return None
    features = set(assessment.get('visible_features') or ())
    matches = [pattern for pattern in PATTERNS if crop in pattern.crops and pattern.part == assessment.get('part')
               and any(features.issuperset(group) for group in pattern.combinations)]
    if len(matches) != 1:
        return None
    pattern = matches[0]
    explanation, check = pattern.bn if locale == 'bn' else pattern.en
    return {'possible_explanation': explanation, 'next_check': check, 'source_url': pattern.source}
