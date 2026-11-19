"""Pinned, crop-aware research inference. Never conditions scores on a chosen crop."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat
from . import doctor_vision
from .services import ModelBrokenError

CATALOG = json.loads(Path(__file__).with_name('doctor_catalog.json').read_text(encoding='utf-8'))
CROPS = {c['id']: c for c in CATALOG['crops']}
PLANT_LABELS = CATALOG['models']['plantvillage']['labels']
RICE_LABELS = CATALOG['models']['rice']['labels']
NOTICE = 'Research screening only. Crop identification and out-of-distribution rejection are not field-validated.'
_LOCK = threading.RLock()
_CACHE: dict[tuple, dict] = {}


def normalize_crop(value: str) -> str:
    value = str(value).strip().lower()
    value = {'corn': 'maize', 'pepper': 'bell_pepper', 'bell pepper': 'bell_pepper', 'paddy': 'rice'}.get(value, value)
    if value not in CROPS:
        raise ValueError('Unsupported crop. Choose a disease-enabled crop from the capability catalog.')
    return value


def crop_for_label(label: str) -> str | None:
    prefix = label.split('___', 1)[0]
    return next((c['id'] for c in CROPS.values() if c['label_prefix'] == prefix), None)


def classify_logits(logits, labels: list[str], crop: str, threshold: float) -> dict:
    import torch
    if logits.ndim != 1 or logits.numel() != len(labels):
        raise ValueError('Model output shape does not match class metadata')
    if not bool(torch.isfinite(logits).all()):
        raise ValueError('Model output must be finite')
    probs = logits.float().softmax(0)
    indices = probs.argsort(descending=True)[:3].tolist()
    crop_indices = [i for i, label in enumerate(labels) if crop_for_label(label) == crop]
    crop_indices.sort(key=lambda i: float(probs[i]), reverse=True)
    index = indices[0]
    score = float(probs[index])
    reason = 'crop_mismatch' if crop_for_label(labels[index]) != crop else ('low_confidence' if score < threshold else None)
    return dict(top_label='unknown' if reason else labels[index], abstained=bool(reason), score=score,
        score_type='uncalibrated_model_score', rejection_reason=reason, ood_notice=NOTICE,
        alternatives=[{'label': labels[i], 'score': float(probs[i])} for i in indices],
        selected_crop_options=[{'label': labels[i], 'score': float(probs[i])} for i in crop_indices[:3]])


def image_quality(image: Image.Image) -> list[str]:
    gray = image.convert('L'); stats = ImageStat.Stat(gray)
    flags = []
    if min(image.size) < 160: flags.append('low_resolution')
    if stats.mean[0] < 35: flags.append('underexposed')
    if stats.mean[0] > 235: flags.append('overexposed')
    inner = gray.crop((2, 2, max(3, gray.width-2), max(3, gray.height-2))) if min(gray.size)>6 else gray
    if stats.var[0] < 8 or ImageStat.Stat(inner.filter(ImageFilter.FIND_EDGES)).var[0] < 80:
        flags.append('possibly_blurred')
    return flags


class DoctorRegistry:
    def __init__(self, root: Path | str | None = None):
        configured = root or os.getenv('MULTICROP_MODEL_DIR')
        if configured:
            self.root = Path(configured)
        else:
            # Source checkout and /app/app container layouts have different depths.
            repo = next((p for p in Path(__file__).resolve().parents if (p/'ml/artifacts').is_dir()), None)
            self.root = repo/'ml/artifacts/multicrop' if repo else Path('/models/multicrop').resolve()

    def _bundle(self, model_id: str) -> dict:
        spec = CATALOG['models'][model_id]
        folder = self.root / model_id
        card_path, binary = folder/'model.json', folder/'model.pt'
        base = dict(version=f'{model_id}-{spec["revision"][:12]}', available=False,
            field_validated=False, labels=spec['labels'], metrics=None, reported_metrics=None,
            source=spec['source_repo'], source_url=spec['source_url'], license=spec['license'],
            revision=spec['revision'], model_id=model_id, threshold=spec['threshold'],
            limitations=[NOTICE, 'Publisher metrics are external reports, not AgroSphere field validation.'],
            artifact_status='absent', artifact_error=None)
        if not card_path.is_file() and not binary.is_file():
            return {'card':base}
        try:
            raw = card_path.read_bytes()
            stat = binary.stat()
            key = (str(folder.resolve()), hashlib.sha256(raw).hexdigest(), stat.st_size, stat.st_mtime_ns)
        except OSError as exc:
            return {'card':{**base,'artifact_status':'broken_artifact','artifact_error':str(exc)}}
        # Single-flight initialization: public capability checks cannot duplicate cold loads.
        with _LOCK:
            if key in _CACHE: return _CACHE[key]
            try:
                card = json.loads(raw)
                for field in ['model_id','source_repo','revision','source_sha256','license']:
                    if card.get(field) != spec[field]:
                        raise ValueError(f'{field} does not match the pinned model source')
                if card.get('source_sha256_verified') != spec['source_sha256']:
                    raise ValueError('Verified source checksum does not match pinned weights')
                if card.get('labels') != spec['labels'] or len(set(card['labels'])) != len(card['labels']):
                    raise ValueError('Class labels/order do not match the pinned catalog')
                if card.get('preprocessing') != spec['preprocessing']:
                    raise ValueError('Preprocessing does not match pinned metadata')
                if card.get('threshold') != spec['threshold']:
                    raise ValueError('Threshold does not match declared research policy')
                if hashlib.sha256(binary.read_bytes()).hexdigest() != card.get('artifact_sha256'):
                    raise ValueError('Model artifact checksum mismatch')
                import torch
                from torchvision import transforms
                torch.set_num_threads(2)
                model = torch.jit.load(str(binary), map_location='cpu').eval()
                with torch.inference_mode(): output = model(torch.zeros(1,3,224,224))
                if tuple(output.shape) != (1,len(spec['labels'])) or not bool(torch.isfinite(output).all()):
                    raise ValueError('Model output shape/values are invalid')
                prep = spec['preprocessing']
                interpolation = transforms.InterpolationMode.BICUBIC if prep['interpolation']=='bicubic' else transforms.InterpolationMode.BILINEAR
                transform = transforms.Compose([transforms.Resize(prep['resize'], interpolation=interpolation),
                    transforms.CenterCrop(prep['crop']), transforms.ToTensor(), transforms.Normalize(prep['mean'],prep['std'])])
                entry = {'card':{**base, **card, 'metrics':None, 'available':True, 'artifact_status':'ready',
                    'field_validated':False,'artifact_error':None}, 'model':model,'transform':transform}
            except Exception as exc:
                entry = {'card':{**base, 'artifact_status':'broken_artifact','artifact_error':str(exc)}}
            _CACHE[key] = entry
            return entry

    def card(self, crop: str = 'tomato') -> dict:
        crop = normalize_crop(crop)
        if doctor_vision.configured():
            return {**doctor_vision.model_card(), 'supported_crop_ids': list(CROPS)}
        card = dict(self._bundle(CROPS[crop]['model_id'])['card'])
        card['supported_crop_ids'] = [c['id'] for c in CROPS.values() if c['model_id']==card['model_id']]
        return card

    def capabilities(self) -> dict:
        if doctor_vision.configured():
            card = doctor_vision.model_card()
            crops = [{**crop, 'model_id': card['model_id'], 'model_version': card['version'],
                      'available': True, 'artifact_status': 'configured', 'labels': [],
                      'has_healthy_class': False, 'limitations': card['limitations']} for crop in CROPS.values()]
            return {'provider': 'groq', 'crops': crops, 'models': [card],
                    'limitations': card['limitations'], 'automatic_crop_detection': True}
        cards = {mid:self._bundle(mid)['card'] for mid in CATALOG['models']}
        crops = []
        for crop in CROPS.values():
            card = cards[crop['model_id']]
            labels = [label for label in card['labels'] if label.startswith(crop['label_prefix']+'___')]
            healthy = any(label.lower().endswith('___healthy') for label in labels)
            crops.append({**crop, 'labels':labels, 'available':card['available'], 'model_version':card['version'],
                'artifact_status':card['artifact_status'], 'has_healthy_class':healthy,
                'limitations':[NOTICE]+([] if healthy else ['This crop has no healthy reference class; a healthy plant cannot be ruled in/out.'])})
        return {'crops':crops,'models':list(cards.values()),'limitations':[NOTICE], 'automatic_crop_detection':False}

    def screen_with_vision(self, image: Image.Image, crop: str, part: str, locale: str,
                           follow_up: Image.Image | None = None) -> dict:
        bn = locale == 'bn'
        result = doctor_vision.inspect_photo(image, crop, part, 'Bangla' if bn else 'English', follow_up)
        assessment = result['assessment']
        if assessment['outcome'] != 'no_visible_damage' or assessment['part'] != 'leaf':
            return result

        # A false healthy result can hide a lesion. Only corroborate a negative using a
        # matching leaf classifier with a healthy class. Never run it on harvested produce.
        checks = []
        if crop in CROPS and assessment['crop_match'] == 'match':
            spec = CATALOG['models'][CROPS[crop]['model_id']]
            healthy_label = CROPS[crop]['label_prefix'] + '___healthy'
            if any(label.casefold() == healthy_label.casefold() for label in spec['labels']):
                try:
                    for photo in (image, follow_up) if follow_up is not None else (image,):
                        checks.append(self.infer(photo, crop))
                except ModelBrokenError:
                    pass
        reason = 'unconfirmed_leaf_screen'
        labels = [check['classification']['top_label'].lower() for check in checks
                  if not check['classification']['abstained']]
        if labels:
            result['cross_check_model'] = checks[0]['model']['version']
            if len(labels) == (2 if follow_up is not None else 1) and all(label.endswith('___healthy') for label in labels):
                return result
            if any(not label.endswith('___healthy') for label in labels):
                reason = 'model_disagreement'
        explanation = ('ছবিতে ক্ষতি আছে কি না তা নিশ্চিত করা যায়নি।' if bn else
                       'The photo does not give enough evidence to rule out leaf damage.')
        if reason == 'model_disagreement':
            explanation = ('গ্রক ভিশন স্পষ্ট ক্ষতি শনাক্ত করেনি, কিন্তু পাতার দ্বিতীয় মডেলটি ক্ষতির ইঙ্গিত দিয়েছে।' if bn else
                           'Groq did not identify clear damage, but the independent leaf classifier flagged a possible lesion.')
        advice = ['আক্রান্ত অংশ ও পাতার উল্টো পাশের কাছ থেকে পরিষ্কার ছবি তুলুন।' if bn else
                  'Take a close-up of the affected area and another photo of the underside.']
        assessment.update(outcome='uncertain', condition=None, distinguishing_sign=None, marker='nonspecific',
                          pattern='অনিশ্চিত' if bn else 'Uncertain', signs=[], explanation=explanation,
                          uncertainty='কারণ নির্ধারণ করা যায়নি।' if bn else 'The cause is unresolved.', next_steps=advice)
        result['classification'].update(top_label='unknown', abstained=True, rejection_reason=reason)
        result.update(status='unable_to_classify', advice=advice)
        return result

    def infer(self, image: Image.Image, crop: str) -> dict:
        crop = normalize_crop(crop)
        flags = image_quality(image)
        bundle = self._bundle(CROPS[crop]['model_id']); card = dict(bundle['card'])
        result = dict(top_label='unknown', abstained=True, score=None, score_type='not_available',
            alternatives=[], rejection_reason='image_quality' if flags else 'model_unavailable', ood_notice=NOTICE)
        if not flags:
            if not card['available']:
                raise ModelBrokenError('The selected crop model is unavailable. Install/verify its pinned bundle before screening.')
            try:
                import torch
                with torch.inference_mode(): logits = bundle['model'](bundle['transform'](image).unsqueeze(0))[0]
                result = classify_logits(logits, card['labels'], crop, card['threshold'])
            except Exception as exc:
                raise ModelBrokenError(f'Crop model inference failed safely: {exc}') from exc
        return dict(crop=crop, classification=result, model=card, quality_flags=flags,
            status='unable_to_classify' if result['abstained'] else 'completed',
            advice=[f'Confirm this is a {CROPS[crop]["name_en"].lower()} leaf; check several leaves in natural light.',
                'Record symptoms and photograph both sides of affected leaves; inspect neighbouring plants.',
                'Consult a qualified local agronomist or DAE extension officer before treatment decisions.'],
            disclaimer=NOTICE+' No treatment or pesticide dosing is prescribed.')
