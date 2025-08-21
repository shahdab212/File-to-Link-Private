import unittest
from unittest.mock import patch, MagicMock
from bot_main import FileLinkBot

class TestFileLinkBot(unittest.TestCase):
    
    @patch('bot_main.Client')
    def setUp(self, MockClient):
        self.bot = FileLinkBot()
        self.bot.bot = MockClient()
    
    def test_generate_file_id(self):
        message = MagicMock()
        message.chat.id = 12345
        message.id = 67890
        file_id = self.bot.generate_file_id(message)
        self.assertEqual(file_id, "12345_67890")
    
    def test_get_file_info_video(self):
        message = MagicMock()
        # Set up the message to have a video attribute but no document attribute
        message.document = None
        message.video = MagicMock()
        message.video.file_name = "test_video.mp4"
        message.video.file_size = 5000000
        message.video.mime_type = "video/mp4"
        message.video.file_id = "test_file_id"
        message.audio = None
        
        file_info = self.bot.get_file_info(message)
        self.assertEqual(file_info['type'], 'video')
        self.assertEqual(file_info['name'], "test_video.mp4")
        self.assertEqual(file_info['size'], 5000000)
        self.assertEqual(file_info['mime_type'], "video/mp4")
    
    def test_get_file_info_document(self):
        message = MagicMock()
        # Set up the message to have a document attribute but no video/audio attributes
        message.document = MagicMock()
        message.document.file_name = "test_document.pdf"
        message.document.file_size = 3000000
        message.document.mime_type = "application/pdf"
        message.document.file_id = "test_doc_id"
        message.video = None
        message.audio = None
        
        file_info = self.bot.get_file_info(message)
        self.assertEqual(file_info['type'], 'document')
        self.assertEqual(file_info['name'], "test_document.pdf")
        self.assertEqual(file_info['size'], 3000000)
        self.assertEqual(file_info['mime_type'], "application/pdf")

    def test_get_file_info_audio(self):
        message = MagicMock()
        # Set up the message to have an audio attribute but no document/video attributes
        message.document = None
        message.video = None
        message.audio = MagicMock()
        message.audio.file_name = "test_audio.mp3"
        message.audio.file_size = 2000000
        message.audio.mime_type = "audio/mpeg"
        message.audio.file_id = "test_audio_id"
        
        file_info = self.bot.get_file_info(message)
        self.assertEqual(file_info['type'], 'audio')
        self.assertEqual(file_info['name'], "test_audio.mp3")
        self.assertEqual(file_info['size'], 2000000)
        self.assertEqual(file_info['mime_type'], "audio/mpeg")

    def test_get_file_info_none(self):
        message = MagicMock()
        # Set up the message to have no file attributes
        message.document = None
        message.video = None
        message.audio = None
        
        file_info = self.bot.get_file_info(message)
        self.assertIsNone(file_info)

if __name__ == '__main__':
    unittest.main()
