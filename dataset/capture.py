"""Originales PNG y manifiesto CSV; etiquetas humanas, sin overlays."""
import csv
from datetime import datetime, timezone
from pathlib import Path
import re
import threading
import time
import uuid
import json
import cv2

SHAPES = ('cubo', 'cilindro', 'prisma_triangular')
COLORS = ('rojo', 'verde', 'azul')
FIELDS = ('image', 'shape', 'color', 'session', 'captured_utc', 'frame_id',
          'received_monotonic', 'age_at_save_s', 'width', 'height', 'source')


class DatasetCapture:
    def __init__(self, destination):
        self.root = Path(destination)
        self.lock = threading.RLock()

    def save_record(self, frame, shape, color, session, config, guard=lambda: None):
        from ai.perception import Perception
        from ai.transforms import crop_bounds
        from dataset.quality import measure
        from dataset.tools import review
        result=Perception(config['vision']).process(frame)
        with self.lock:
            previous=review(self.root)
            quality=measure(frame.image,config['dataset_options'],result.observation.objects,
                            [r['quality'] for r in previous if r.get('quality')])
            if quality['rejections']: raise ValueError('; '.join(quality['rejections']))
            guard()
            path=self.save(frame,shape,color,session,max_age=config['frame_max_age_s'],source=frame.source)
            record={'schema_version':2,'id':path.stem,'original':path.relative_to(self.root).as_posix(),
                'frame_id':frame.id,'camera_generation':frame.generation,'source':frame.source,
                'shape':shape,'color':color,'session':session,'received_at':frame.received_at,
                'transform':config['vision'],'quality':quality,'review':'sin_revisar','crop':None,'roi':None}
            # Se recorta la imagen normalizada SIN filtros digitales ni overlays.
            candidates=[o for o in result.observation.objects if o.color==color]
            if candidates:
                target=max(candidates,key=lambda o:o.area)
                x1,y1,x2,y2=crop_bounds(target.box,result.observation.dimensions,config['vision']['crop_margin'])
                crop=result.normalized[y1:y2,x1:x2]
                folder=self.root/'derived'/shape/session;folder.mkdir(parents=True,exist_ok=True)
                cp=folder/(path.stem+'.png'); ok,blob=cv2.imencode('.png',crop)
                if not ok: raise OSError('No se pudo codificar recorte')
                temp=cp.with_suffix('.tmp');temp.write_bytes(blob.tobytes());temp.replace(cp)
                record.update(crop=cp.relative_to(self.root).as_posix(),roi=[x1,y1,x2,y2])
            with (self.root/'metadata'/'vision_v2.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            return path,record

    def save(self, frame, shape, color, session, max_age=.8, source='camara_real'):
        if shape not in SHAPES or color not in COLORS:
            raise ValueError('Forma o color inválidos')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', session):
            raise ValueError('Sesión: 1–64 letras ASCII, números, guion o guion bajo')
        age = time.monotonic() - frame.received_at
        if age < 0 or age > max_age:
            raise ValueError('Fotograma atrasado; capture uno nuevo')
        if source not in ('camara_real', 'fixture_prueba'):
            raise ValueError('Fuente no reconocida')
        with self.lock:
            folder = self.root / 'images' / shape / session
            metadata = self.root / 'metadata' / 'manifest.csv'
            folder.mkdir(parents=True, exist_ok=True)
            metadata.parent.mkdir(parents=True, exist_ok=True)
            filename = folder / (uuid.uuid4().hex + '.png')
            ok, blob = cv2.imencode('.png', frame.image)
            if not ok:
                raise OSError('No se pudo codificar PNG')
            temp = filename.with_suffix('.tmp')
            try:
                temp.write_bytes(blob.tobytes())
                temp.replace(filename)
                new = not metadata.exists() or metadata.stat().st_size == 0
                with metadata.open('a', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=FIELDS)
                    if new:
                        writer.writeheader()
                    h, w = frame.image.shape[:2]
                    writer.writerow(dict(zip(FIELDS, [filename.relative_to(self.root).as_posix(),
                        shape, color, session, datetime.now(timezone.utc).isoformat(), frame.id,
                        frame.received_at, age, w, h, source])))
            except Exception:
                filename.unlink(missing_ok=True)
                temp.unlink(missing_ok=True)
                raise
            return filename

    def counts(self):
        result = dict.fromkeys(SHAPES, 0)
        manifest = self.root / 'metadata' / 'manifest.csv'
        if manifest.exists():
            with manifest.open(newline='', encoding='utf-8') as stream:
                for row in csv.DictReader(stream):
                    if row.get('shape') in result and row.get('source') == 'camara_real' and (self.root / row['image']).is_file():
                        result[row['shape']] += 1
        return result
