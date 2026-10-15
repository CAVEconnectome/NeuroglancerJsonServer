if [ -n "$NGLSTATE_BUCKET_PATH" ]; then
  echo "Skipping Google Datastore bucket initialization for S3-backed NGLState"
else
  sleep 10
  python configure_bucket.py
fi
