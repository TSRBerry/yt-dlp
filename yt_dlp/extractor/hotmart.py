import re

from .common import InfoExtractor
from ..utils import get_element_by_id, traverse_obj, get_elements_html_by_class, extract_attributes


class HotmartIE(InfoExtractor):
    _VALID_EMBED_BASE_URL = r'player\.hotmart\.com/embed/(?P<id>[a-zA-Z0-9]+)'
    _VALID_EMBED_URL = r'https?://%s' % _VALID_EMBED_BASE_URL
    _VALID_BASE_API_URL = r'[^/]+/api/v2/hotmart/private_video\?attachment_id=(?P<attachment_id>\d+)'
    _VALID_API_URL = r'https?://%s' % _VALID_BASE_API_URL
    _VALID_URL = r'''(?x)
        https?://
            (?:%s|%s)
        ''' % (_VALID_EMBED_BASE_URL, _VALID_BASE_API_URL)
    _EMBED_REGEX = [
        r'''(?x)
            <iframe[^>]+?src=["\']
            (?P<url>%s)
            ''' % _VALID_EMBED_URL]
    # _TESTS = [{
    #     'url': 'https://yourextractor.com/watch/42',
    #     'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
    #     'info_dict': {
    #         'id': '42',
    #         'ext': 'mp4',
    #         'title': 'Video title goes here',
    #         'thumbnail': r're:^https?://.*\.jpg$',
    #         # TODO more properties, either as:
    #         # * A value
    #         # * MD5 checksum; start the string with md5:
    #         # * A regular expression; start the string with re:
    #         # * Any Python type (for example int or float)
    #     }
    # }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        base_url = re.search(r'https?://(?P<url>[^/]+)', url).group('url')
        urls = list(super()._extract_embed_urls(url, webpage))

        # Original analysis here: https://github.com/yt-dlp/yt-dlp/issues/3564#issuecomment-1146929281

        # If this fails someone needs to find the new location of the data-attachment-id to give to API
        #  ... or the user doesn't have access to the lecture -- using older code to detect this
        container_elements = get_elements_html_by_class('hotmart_video_player', webpage)
        for container_element in container_elements:
            # If this fails the API might use a different method of getting the hotmart video than the attachment-id
            container_attributes = extract_attributes(container_element)
            attachment_id = container_attributes['data-attachment-id']

            # Currently holds no security and will return good data to construct video link for any valid attachment-id,
            #  else a 404
            urls.append(f'https://{base_url}/api/v2/hotmart/private_video?attachment_id={attachment_id}')

        return urls

    def _real_extract(self, url):
        api_url_match = re.match(self._VALID_API_URL, url)
        if api_url_match:
            # Not adding error checking for video_id, signature, and teachable_application_key
            #  because they seem to always be there unless there's the 404
            # Tested one includes status: "READY", and upload_retries_cap_reached: false as well

            # Use attachment-id as video_id for now
            attachment_id = api_url_match.group('attachment_id')
            video_url_data = self._download_json(url, attachment_id)

            url = (f'https://player.hotmart.com/embed/{video_url_data["video_id"]}?'
                   f'signature={video_url_data["signature"]}&'
                   f'token={video_url_data["teachable_application_key"]}')

        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_data_string = get_element_by_id('__NEXT_DATA__', webpage)
        video_data = self._parse_json(video_data_string, video_id)

        # Encrypted url is 'urlEncrypted' instead of 'url'
        # See https://github.com/yt-dlp/yt-dlp/issues/3564 for initial discussion of design
        url = traverse_obj(video_data, ('props', 'pageProps', 'applicationData', 'mediaAssets', 0, 'url'))
        thumbnail_url = traverse_obj(video_data, ('props', 'pageProps', 'applicationData', 'urlThumbnail'))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')

        return {
            'id': video_id,
            'video_id': video_id,
            'thumbnail': thumbnail_url,
            'formats': formats,
            'subtitles': subtitles
        }
