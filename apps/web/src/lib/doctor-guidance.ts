type CropGuide = {
  inspect: string;
  action: string;
  source: string;
  conditions: Record<string, [signs: string, action: string]>;
};

const blights: CropGuide['conditions'] = {
  Early_blight: ['Check older leaves for brown spots with concentric rings.', 'Water at soil level and handle plants when the foliage is dry.'],
  Late_blight: ['Look for dark, irregular patches that spread quickly and white growth underneath leaves in damp weather.', 'Keep foliage dry and contact your local agricultural extension office promptly if these signs are spreading.'],
};
const orchard = 'https://content.ces.ncsu.edu/disease-and-insect-management-in-the-home-orchard';
const vegetables = 'https://extension.rutgers.edu/fs1124';

export const potatoFieldChecks = [
  {
    en: {
      title: 'Upward-rolling leaves · potato leafroll',
      signs: 'Check whether several leaflets roll upward and whether the plant is unusually upright or stunted. Compare it with a nearby healthy-looking plant.',
      action: 'Photograph the whole plant and the stem at soil level. Ask an extension officer to distinguish leafroll from stem disease or growing stress.',
    },
    bn: {
      title: 'পাতা ওপরের দিকে গুটিয়ে যাওয়া · আলুর পাতা মোড়ানো রোগ',
      signs: 'একাধিক পত্রক ওপরের দিকে গুটিয়েছে কি না এবং গাছ অস্বাভাবিকভাবে খাড়া বা খাটো কি না দেখুন। পাশের সুস্থ দেখায় এমন গাছের সঙ্গে তুলনা করুন।',
      action: 'পুরো গাছ ও মাটির কাছের কাণ্ডের ছবি তুলুন। পাতা মোড়ানো রোগ, কাণ্ডের রোগ ও পরিবেশগত চাপ আলাদা করতে কৃষি কর্মকর্তার সাহায্য নিন।',
    },
    source: 'https://ipm.ucanr.edu/agriculture/potato/leafroll/',
  },
  {
    en: {
      title: 'Patchy light and dark green · virus-like mosaic',
      signs: 'Look for irregular light and dark green patches and puckering on several leaves.',
      action: 'Photograph affected and healthy-looking leaves. Ask an extension officer whether a lab test is needed to tell viruses such as PVY and PVX apart.',
    },
    bn: {
      title: 'হালকা ও গাঢ় সবুজ ছোপ · ভাইরাসের মতো মোজাইক লক্ষণ',
      signs: 'কয়েকটি পাতায় অনিয়মিত হালকা ও গাঢ় সবুজ ছোপ এবং কুঁচকে যাওয়া আছে কি না দেখুন।',
      action: 'আক্রান্ত ও সুস্থ দেখায় এমন পাতার ছবি তুলুন। PVY ও PVX-এর মতো ভাইরাস আলাদা করতে পরীক্ষাগারের পরীক্ষা দরকার কি না কৃষি কর্মকর্তাকে জিজ্ঞেস করুন।',
    },
    source: 'https://ipm.ucanr.edu/agriculture/potato/Mosaic-Diseases-Caused-By-Potyviruses/',
  },
  {
    en: {
      title: 'Wilting with a black stem base · blackleg',
      signs: 'Look for a black patch on the stem where it meets the soil, especially if the leaves are also yellowing or wilting.',
      action: 'Take a close-up of the stem base and a photo of the whole plant. Arrange an extension review if several plants are wilting.',
    },
    bn: {
      title: 'গাছ ঢলে পড়া ও কাণ্ডের গোড়া কালো · ব্ল্যাকলেগ',
      signs: 'মাটির ঠিক ওপরে কাণ্ডে কালো দাগ আছে কি না দেখুন, বিশেষ করে পাতা হলুদ হলে বা গাছ ঢলে পড়লে।',
      action: 'কাণ্ডের গোড়ার কাছ থেকে এবং পুরো গাছের ছবি তুলুন। কয়েকটি গাছ ঢলে পড়লে কৃষি কর্মকর্তার সাহায্য নিন।',
    },
    source: 'https://extension.umaine.edu/publications/2493e/',
  },
];

export const cropGuides: Record<string, CropGuide> = {
  apple: {
    inspect: 'Compare spots on leaves with marks on fruit. Look for olive patches, orange spots, or rings.',
    action: 'Photograph the leaves and fruit and check the tree for dead wood and shriveled fruit.',
    source: orchard,
    conditions: {
      Apple_scab: ['Look for olive or dark velvety leaf spots and corky patches on fruit.', 'Clear fallen leaves and favor airflow through the canopy.'],
      Black_rot: ['Look for ringed leaf spots, rotting fruit, and shriveled fruit left on the tree.', 'Remove mummified fruit and ask about pruning dead or cankered wood.'],
      Cedar_apple_rust: ['Look for bright yellow to orange leaf spots.', 'Photograph both sides and ask extension to confirm rust before changing orchard management.'],
    },
  },
  cherry: {
    inspect: 'Look closely at the undersides of young leaves and at new shoots.',
    action: 'Photograph several shoots and check whether symptoms cluster in dense, shaded growth.',
    source: 'https://ipm.ucanr.edu/home-and-landscape/powdery-mildew-on-fruits-and-berries/',
    conditions: {
      Powdery_mildew: ['Look for white powdery patches and distorted young leaves.', 'Improve canopy airflow and ask about locally suitable resistant varieties for future planting.'],
    },
  },
  maize: {
    inspect: 'Check both sides of lower leaves, then check whether lesions have reached the ear leaf.',
    action: 'Record crop stage and how many plants are affected. Ask extension about local risk if damage is moving up the canopy.',
    source: 'https://www.vegetables.cornell.edu/pest-management/disease-factsheets/sweet-corn-diseases-and-control-measures/',
    conditions: {
      'Cercospora_leaf_spot Gray_leaf_spot': ['Look for rectangular gray or tan lesions bounded by veins.', 'Ask about rotation and resistant hybrids for fields with recurring gray leaf spot.'],
      Common_rust_: ['Look for raised reddish-brown pustules on both sides of the leaf.', 'Scout nearby plants and get confirmation if pustules are dense or spreading.'],
      Northern_Leaf_Blight: ['Check for long, cigar-shaped gray-green or tan lesions.', 'Track whether lesions reach the ear leaf and ask about resistant hybrids for future planting.'],
    },
  },
  grape: {
    inspect: 'Compare several leaves and photograph any marked berries or affected canes.',
    action: 'Mark affected vines and record whether damage appears on one arm or across the planting.',
    source: 'https://www.apsnet.org/edcenter/resources/commonnames/Pages/Grape.aspx',
    conditions: {
      Black_rot: ['Check leaves for tan spots with tiny dark dots and fruit for dark, shriveled berries.', 'Remove mummified berries and seek confirmation if clusters are affected.'],
      'Esca_(Black_Measles)': ['Look for stripes of yellowing or browning between veins.', 'Mark affected vines for inspection. Ask extension to check the wood before major pruning.'],
      'Leaf_blight_(Isariopsis_Leaf_Spot)': ['Check for dark, irregular leaf blotches and compare older and younger leaves.', 'Photograph both sides and have the spots checked because several grape diseases look alike.'],
    },
  },
  orange: {
    inspect: 'Compare the two sides of the midrib for uneven yellow blotches and inspect fruit shape.',
    action: 'Keep suspect plants and graft material in place and contact your local extension office for confirmation.',
    source: 'https://gardeningsolutions.ifas.ufl.edu/care/pests-and-diseases/diseases/citrus-greening-faq/',
    conditions: {
      'Haunglongbing_(Citrus_greening)': ['Look for uneven yellow mottling, small lopsided fruit, or fruit that stays partly green.', 'Avoid moving or propagating suspect plants. Ask extension about testing and local guidance.'],
    },
  },
  peach: {
    inspect: 'Check leaf spots alongside marks on the fruit and twigs.',
    action: 'Photograph different affected branches and record whether symptoms followed wet weather.',
    source: orchard,
    conditions: {
      Bacterial_spot: ['Look for small angular leaf spots that may fall out and pitted marks on fruit.', 'Reduce overhead irrigation where practical and ask extension to distinguish bacterial spot from other shot-hole symptoms.'],
    },
  },
  bell_pepper: {
    inspect: 'Check young and older leaves and photograph any rough marks on the fruit.',
    action: 'Water near the soil and avoid handling wet foliage while you check nearby plants.',
    source: vegetables,
    conditions: {
      Bacterial_spot: ['Look for small dark leaf spots and raised or scabby spots on the fruit.', 'Avoid overhead watering and working among wet plants. Ask extension to confirm if symptoms spread.'],
    },
  },
  potato: {
    inspect: 'Compare older and newer leaves and photograph their undersides. For symptoms on the potato itself, share tuber photos with an extension officer.',
    action: 'Keep foliage dry and ask extension for prompt review if dark patches spread quickly.',
    source: 'https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/late-blight',
    conditions: blights,
  },
  squash: {
    inspect: 'Check the upper and lower surfaces of older leaves for developing patches.',
    action: 'Improve airflow between plants and scout nearby squash for similar symptoms.',
    source: vegetables,
    conditions: {
      Powdery_mildew: ['Look for patches of white powdery growth that spread across the leaf surface.', 'Reduce crowding and ask about resistant varieties for future plantings.'],
    },
  },
  strawberry: {
    inspect: 'Compare several leaves for small purple spots and drying edges.',
    action: 'Reduce prolonged leaf wetness and take photos from several plants before deciding how to manage the patch.',
    source: 'https://ipm.ucanr.edu/home-and-landscape/leaf-scorch-of-strawberries/',
    conditions: {
      Leaf_scorch: ['Look for scattered purple spots that merge and give the leaf a scorched appearance.', 'Improve airflow and water at soil level where practical. Ask extension to distinguish scorch from other leaf spots.'],
    },
  },
  tomato: {
    inspect: 'Compare spots and yellowing on older leaves with any curling or mottling on new growth.',
    action: 'Photograph undersides and fruit, water at soil level, and ask extension about symptoms spreading rapidly.',
    source: vegetables,
    conditions: {
      ...blights,
      Bacterial_spot: ['Look for dark leaf spots and rough, raised marks on fruit.', 'Keep foliage dry and avoid handling wet plants.'],
      Leaf_Mold: ['Look for pale yellow patches above and olive-colored growth underneath.', 'Increase ventilation and reduce prolonged humidity around plants.'],
      Septoria_leaf_spot: ['Check lower leaves for many small spots with pale centers and dark margins.', 'Water at soil level and reduce soil splash with mulch.'],
      'Spider_mites Two-spotted_spider_mite': ['Look for fine pale stippling and webbing underneath leaves.', 'Check nearby plants with a hand lens and ask extension about conserving natural enemies.'],
      Target_Spot: ['Look for brown spots with rings and check stems and fruit for lesions.', 'Improve airflow and ask extension to distinguish it from early blight.'],
      Tomato_Yellow_Leaf_Curl_Virus: ['Look for yellowing, upward curling on young leaves, and stunted growth.', 'Check for whiteflies and get local confirmation before moving seedlings.'],
      Tomato_mosaic_virus: ['Look for uneven light and dark green mottling and distorted leaves.', 'Clean tools and avoid handling healthy plants after touching suspect plants. Arrange diagnostic review.'],
    },
  },
  rice: {
    inspect: 'Compare several hills and photograph the leaf tips, sheaths near the water line, and panicles if present.',
    action: 'Mark affected patches and note crop stage and how quickly symptoms are spreading. Share the pictures with a local rice adviser.',
    source: 'https://rice-diseases.irri.org/contents',
    conditions: {
      Bacterial_Blight: ['Check for elongated yellowing along leaf tips and margins.', 'Get early confirmation if symptoms are expanding and review nitrogen management with an adviser.'],
      Bacterial_Streak: ['Look for narrow, translucent streaks running between veins.', 'Photograph leaves against light and seek confirmation before making a spray decision.'],
      Bakanae: ['Look for unusually tall, pale, thin seedlings compared with nearby plants.', 'Flag affected hills and discuss clean seed for the next planting.'],
      Brown_Spot: ['Look for small round to oval brown spots on leaves.', 'Ask about field nutrition and seed health because stressed plants may be more affected.'],
      False_Smut: ['Check panicles for swollen colored spore balls replacing individual grains.', 'Photograph affected panicles and discuss field and seed management with a rice adviser.'],
      Grassy_Stunt_Virus: ['Look for short plants with excess tillers and narrow, yellowish leaves.', 'Check nearby hills for planthoppers and ask extension to confirm the cause.'],
      Hispa: ['Look for whitish scrape marks or mines in the leaves.', 'Check for beetles and damage in nearby hills and ask extension whether intervention is warranted.'],
      Leaf_Blast: ['Look for pointed, spindle-shaped spots with pale centers.', 'Monitor new lesions and ask extension to assess local blast risk.'],
      Leaf_Scald: ['Look for expanding discolored bands starting near tips or margins.', 'Photograph the transition from damaged to healthy tissue for diagnostic review.'],
      Narrow_Brown_Spot: ['Check for short, narrow brown marks running parallel to the veins.', 'Record where the spots start and have a rice adviser distinguish them from other streaks.'],
      Neck_Blast: ['Inspect the panicle neck for dark lesions and poorly filled heads.', 'Seek prompt field review if several panicles are affected.'],
      Ragged_Stunt_Virus: ['Look for stunting and twisted or ragged leaves.', 'Check hills for planthoppers and arrange diagnostic confirmation.'],
      Sheath_Blight: ['Look for oval gray-green lesions on lower sheaths near the water line.', 'Track spread upward and review dense growth and nitrogen use with an adviser.'],
      Sheath_Rot: ['Check the upper sheath around the emerging panicle for discoloration or trapped heads.', 'Photograph affected heads and have the sheath problem checked before choosing management.'],
      Stem_Rot: ['Look for dark lesions on lower stems and inspect patches with lodging.', 'Flag affected patches and ask an adviser about field residue and water management.'],
      Tungro: ['Look for patches of stunted plants with yellow to orange leaves.', 'Check for leafhoppers and contact a rice adviser if affected patches expand.'],
    },
  },
};

