from google.oauth2 import service_account
import googleapiclient.discovery
import json
from os import environ

class GooglePlayAPI:
    def __init__(self, key_from_json, package_name):
        # Path to your service account JSON key file
        self.KEY_FROM_JSON = key_from_json

        # Scopes required for accessing the Google Play Developer API
        self.SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

        # Package name of your app
        self.PACKAGE_NAME = package_name

        # Authenticate using service account credentials
        credentials = service_account.Credentials.from_service_account_info(self.KEY_FROM_JSON, scopes=self.SCOPES)

        # Build the Google Play Developer API service
        self.service = googleapiclient.discovery.build('androidpublisher', 'v3', credentials=credentials)

        # Start an edit session
        edit_request = self.service.edits().insert(
            body={}, 
            packageName=self.PACKAGE_NAME
        )
        edit_response = edit_request.execute()

        # Extract the editId from the response
        self.EDIT_ID = edit_response['id']

    def get_tracks(self):
        # Call the 'tracks' resource to retrieve all releases for each track
        response = self.service.edits().tracks().list(packageName=self.PACKAGE_NAME, editId=self.EDIT_ID).execute()

        # Extract the list of tracks
        tracks = response.get('tracks', [])

        return tracks

    def get_max_build_number(self):
        max_build_number = 0
        tracks = self.get_tracks()

        for track in tracks:
            releases = track.get('releases', None)
            if releases:
                for release in releases:
                    versionCode = release.get('versionCodes', None)
                    if versionCode:
                        build_number = int(versionCode[0])
                        if build_number > max_build_number:
                            max_build_number = build_number
        return max_build_number

    def upload_app_bundle(self, name, track, appbundle_path, status):
        # Upload the .app bundle
        media = googleapiclient.http.MediaFileUpload(
            appbundle_path,
            mimetype='application/octet-stream',
            resumable=True
        )
        bundle_response = self.service.edits().bundles().upload(
            packageName=self.PACKAGE_NAME,
            editId=self.EDIT_ID,
            media_body=media
        ).execute()

        # Update track with uploaded bundle
        update_track_request = self.service.edits().tracks().update(
            editId=self.EDIT_ID,
            packageName=self.PACKAGE_NAME,
            track=track,
            body={
                'changesNotSentForReview': True,
                'track': track, 
                'releases': [
                        {   
                            'name': name,
                            'versionCodes': [bundle_response['versionCode']], 
                            'status': status
                    }
                ]
            }
        )
        update_track_response = update_track_request.execute()

        print(update_track_response)

        # Commit the changes
        commit_request = self.service.edits().commit(
            changesNotSentForReview=False,
            packageName=self.PACKAGE_NAME,
            editId=self.EDIT_ID
        )
        commit_response = commit_request.execute()
        
        print(commit_response)

if __name__ == '__main__':


    data_reqested = environ.get('DATA_REQUESTED')
    key_from_json = json.loads(environ.get('KEY_FROM_JSON'))
    package_name = environ.get('PACKAGE_NAME')

    api = GooglePlayAPI(
        key_from_json=key_from_json,
        package_name=package_name,
    )
    
    if data_reqested == "build_number":
        last_build_number = api.get_max_build_number()
        print(f"::set-output name=build_number::{ last_build_number + 1 }")

    elif data_reqested == "upload":
        app_name = environ.get('APP_NAME')
        status = environ.get('STATUS')
        track = environ.get('TRACK')
        appbundle_path = environ.get('APPBUNDLE_PATH')

        upload_status = api.upload_app_bundle(
            name=app_name,
            status=status,
            track=track,
            appbundle_path=appbundle_path
        )