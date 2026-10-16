import base64
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone
from mail_messages import extract_images, read_msg
from data_store import preview_import

class MailTests(unittest.TestCase):
    def attachment(self, raw, name="image.png"):
        return SimpleNamespace(attached_by_value=True,file_bytes=raw,file_name=name)
    def test_images_and_safe_names(self):
        raw=b"\x89PNG\r\n\x1a\nexample"
        result=extract_images([self.attachment(raw,"../../image.png"),self.attachment(b"document","manual.pdf")])
        self.assertEqual(result["files"][0]["name"],"image.png")
        self.assertEqual(base64.b64decode(result["files"][0]["content"]),raw)
        self.assertEqual(result["omitted"],1)
    def test_limits(self):
        result=extract_images([self.attachment(b"\x89PNG\r\n\x1a\n") for _ in range(21)])
        self.assertEqual(len(result["files"]),19)
        self.assertEqual(result["omitted"],2)
    def test_invalid_msg(self):
        with self.assertRaisesRegex(ValueError,"illisible"):
            read_msg(b"invalid")
    def test_preview_date_and_illustrations(self):
        message={"headers":[("Objet","A request")],"body":"Test [cid:illustration]","html":None,"date":datetime(2026,10,14,13,13,tzinfo=timezone.utc),"images":{"files":[{"name":"image.png","content":"abc"}],"omitted":0}}
        with patch("mail_messages.read_msg",return_value=message):
            result=preview_import({"name":"source.msg","content":base64.b64encode(b"source").decode()})
        self.assertEqual(result["time"],"15:13")
        self.assertEqual(len(result["images"]),1)
        self.assertNotIn("cid:",result["text"])
        self.assertEqual(base64.b64decode(result["source"]["content"]),b"source")

if __name__=="__main__":unittest.main()
