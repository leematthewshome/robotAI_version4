# USAGE
# python train_model.py --embeddings output/embeddings.pickle --recognizer output/recognizer.pickle --le output/le.pickle

#=========================================================================
# NOTE: You need to run extract_embeddings.py before running this script.
#=========================================================================

# import the necessary packages
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import pickle
import os

# setup paths to the various files and parameters required
thisdir = os.path.dirname(os.path.realpath(__file__))
embeddings = os.path.join(thisdir, 'output/embeddings.pickle')
recognizer_path = os.path.join(thisdir, 'output/recognizer.pickle')
label_enc = os.path.join(thisdir, 'output/le.pickle')

# load the face embeddings
print("[INFO] loading face embeddings...")
data = pickle.loads(open(embeddings, "rb").read())

# encode the labels
print("[INFO] encoding labels...")
le = LabelEncoder()
labels = le.fit_transform(data["names"])

# train the model used to accept the 128-d embeddings of the face and then produce the actual face recognition
print("[INFO] training model...")
recognizer = SVC(C=1.0, kernel="linear", probability=True)
recognizer.fit(data["embeddings"], labels)

# write the actual face recognition model to disk
f = open(recognizer_path, "wb")
f.write(pickle.dumps(recognizer))
f.close()

# write the label encoder to disk
f = open(label_enc, "wb")
f.write(pickle.dumps(le))
f.close()
