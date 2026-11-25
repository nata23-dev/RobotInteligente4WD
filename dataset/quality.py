"""Indicadores provisionales, no certifican la validez del entrenamiento."""
import hashlib
import cv2
import numpy as np


def measure(image, options, objects=(), previous=()):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h,w = gray.shape
    brightness = float(gray.mean())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    digest = hashlib.sha256(image.tobytes()+str(image.shape).encode()).hexdigest()
    small=cv2.resize(gray,(9,8),interpolation=cv2.INTER_AREA)
    bits=(small[:,1:] > small[:,:-1]).flatten()
    phash=int(''.join('1' if b else '0' for b in bits),2)
    exact=any(r.get('sha256')==digest for r in previous)
    similar=any((phash ^ int(r['dhash'],16)).bit_count() <= options['similarity_distance'] for r in previous if r.get('dhash'))
    warnings=[]
    if w<options['min_width'] or h<options['min_height']: warnings.append('Resolución inferior al perfil')
    if brightness<options['dark_mean']: warnings.append('Exposición insuficiente')
    if brightness>options['bright_mean']: warnings.append('Exposición excesiva')
    if sharpness<options['min_sharpness']: warnings.append('Nitidez baja (varianza de Laplaciano)')
    if exact: warnings.append('Duplicado exacto')
    elif similar: warnings.append('Similitud perceptual alta (dHash)')
    if not objects: warnings.append('Sin objeto segmentado')
    elif max(o.area_ratio for o in objects)<options['min_object_ratio']: warnings.append('Objeto pequeño')
    return {'width':w,'height':h,'brightness_mean':brightness,'sharpness_laplacian':sharpness,
            'sha256':digest,'dhash':f'{phash:016x}','exact_duplicate':exact,'perceptual_similar':similar,
            'object_count':len(objects),'warnings':warnings,
            'rejections':['Duplicado exacto'] if exact and options['reject_exact_duplicates'] else []}
