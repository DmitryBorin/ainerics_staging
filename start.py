from crop_faces import Crop_faces
from connect import Connection

crop_faces = Crop_faces('./crops/', './crops_data.json', './models/model_faces.pb')
connect = Connection('cam1')
