from zoneinfo import ZoneInfo

from media_observer.article import ArchiveCollection

from .france_tv_info import FranceTvInfoFrontPage
from .le_monde import LeMondeFrontPage
from .cnews import CNewsFrontPage
from .bfmtv import BfmTvFrontPage
from .le_parisien import LeParisienFrontPage
from .le_figaro import LeFigaroFrontPage
from .tf1_info import Tf1InfoFrontPage


media_collection = {
    c.name: c
    for c in [
        ArchiveCollection(
            name="france_tv_info",
            url="https://francetvinfo.fr",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=FranceTvInfoFrontPage,
            logo_background_color="#202020",
            logo_src="https://www.francetvinfo.fr/assets/components/headers/header/img/franceinfo-1d7b76a5.svg",
        ),
        ArchiveCollection(
            name="le_monde",
            url="https://lemonde.fr",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=LeMondeFrontPage,
            logo_background_color="#fff",
            logo_content='<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" fill="#1A171B" viewBox="0 0 379.23 81.7"><style>.st0{fill:#8f98a9}.st1{fill:#1a171b}</style><path d="M17.71 57.22c-.11 1.39-.21 2.79-.32 3.76l.21-.22c.86-1.18 1.4-3 1.5-5.69.21-4.4-.75-9.77-1.71-14.93-.97-5.26-1.83-10.63-1.72-15.34.11-2.9.65-5.69 1.83-8.26-2.04 3.11-3.32 6.65-3.43 10.41-.33 9.12 4.07 21.04 3.64 30.27zm28.13-42.83v-.11h.11c-.32-1.5-2.9-4.94-5.79-4.94-.65 0-1.08.11-1.5.22 2.79 1.08 4.94 3.86 5.58 5.79l1.6-.96zM23.3 75.26c-.43.1-.86.1-1.29.1 4.4.76 8.15 3.22 9.55 6.34l1.71-1.07c-1.6-3.33-5.46-5.37-9.97-5.37z" class="st0"/><path d="M21.58 55.18c-.21 3.12-.86 5.37-2.15 7.08l1.29 1.51 7.52-5.48c3.65-2.69 5.69-6.02 5.58-11.81-.11-7.19-3.44-18.25-3.44-26.73 0-7.3 2.79-12.78 9.13-12.78 4.29 0 7.73 4.4 8.26 6.87.22 1.18 0 1.72-1.07 2.47l-3 2.05v3.32l14.92-9.35c-1.93-3.01-7.09-8.58-17.29-8.58-12.23-.1-22.97 9.45-23.4 21.04-.33 9.25 4.08 21.16 3.65 30.39zM74.35 71.5l-7.95-5.48c-.96-.64-1.07-1.28-1.07-2.68v-9.66l20.93-12.77-14.38-15.89-22.44 13.09v3l4.62-2.57v29.74c0 1.71.64 2.79 1.72 3.54l11.92 7.73 16.86-9.77-1.4-3.01-8.81 4.73zm-9.02-37.9.86-.54 8.8 10.2-9.66 6.01V33.6z" class="st1"/><path d="m67.69 38.54.12 2.79 1.92 2.37 1.62-.97zm-16.4 29.74V42.62l-1.08.65-.43.21v25.55c0 2.15 1.18 4.4 2.79 5.48l10.85 7.19 1.39-.86-10.73-7.09c-1.29-.85-2.79-2.46-2.79-5.47z" class="st0"/><path d="M43.69 70.75c-2.47-3.01-6.44-6.55-15.89-6.55-9.98-.11-22.22 7.84-27.8 14.71l.97 1.29c7.62-5.05 15.46-7.3 22.33-7.3 5.58 0 10.2 2.68 12.13 6.65l12.88-8.37-1.29-2.58-3.33 2.15z" class="st1"/><path d="M113.91 75.58c-.65 0-1.29 0-1.94.1 4.51.65 7.09 3.01 7.95 5.8l1.61-.97-.11-.32c-.32-1.07-1.93-4.5-7.51-4.61zm4.08-16.1c1.61-1.72 2.25-4.08 2.25-7.73V20.4c0-3.22-.96-3.54-2.79-3.22h-.22c1.29 1.18 1.51 1.6 1.51 5.36v31.24c0 2.04-.22 3.98-.75 5.7z" class="st0"/><path d="M132.7 70.32c-2.9-3.11-6.98-5.05-12.78-5.05-11.05.11-21.58 8.05-26.09 12.99l1.18 1.5c6.22-4.72 13.73-6.77 19-6.66 5.58.21 8.7 3.32 9.77 6.33l15.14-9.02-1.39-2.79-4.83 2.7z" class="st1"/><path d="M106.29 18.04c-2.05-.54-3.76-1.72-4.73-3.44-1.08-1.93-1.18-4.29-.32-6.76-4.07 5.69-1.29 10.74 5.05 10.2z" class="st0"/><path d="m187.54 70.97-1.4-.75c-1.39-.76-1.72-1.93-1.72-4.51V24.59c0-5.15 1.39-8.48 5.59-10.95l4.39-2.57-1.61-2.69-2.04 1.07c-2.47 1.29-4.19 2.15-7.73.11l-10.42-5.9-13.52 8.37-10.94-8.37-12.67 7.62c-.54-3.87-4.3-10.42-14.49-6.45-2.36.97-5.69 2.26-7.41 2.9-3.65 1.29-5.47-.42-3.22-3.65l1.72-2.47L109.72 0c-3 3.87-4.19 5.48-4.19 5.48-4.83 6.33-1.82 11.38 5.26 10.41 1.72-.21 4.51-.65 6.34-.96 4.83-.86 5.47.96 5.47 5.58v31.34c0 4.29-.75 7.95-4.08 10.53l1.08 1.82 10.74-6.76c4.29-2.68 5.15-6.55 5.15-11.91V14.82l5.48-3.11 4.5 3.65c1.61 1.29 1.94 1.93 1.94 4.83v59.26h.86c4.29-2.25 7.39-3.76 7.39-3.76 3.98-2.04 4.62-2.68 4.62-7.19V15.04l5.69-3.44 12.67 7.41-1.72 1.29c-3 2.25-5.16 5.91-5.16 12.77v36.71c0 3.33.86 5.05 2.91 6.44l4.61 3.12 13.42-8.05-1.29-2.58-3.87 2.26z" class="st1"/><path d="m174.23 19.23-8.26-4.83-1.29.85 8.59 5.05c.32-.44.64-.76.96-1.07zm-4.83 50.55-.11-36.71c0-3.33.43-6.23 1.39-8.59-1.71 2.36-2.79 5.79-2.79 10.73v35.86c0 3.22 1.29 6.12 3.76 7.84l3.76 2.58 1.4-.86-3.43-2.36c-2.8-1.94-3.98-4.52-3.98-8.49zm-28.65-55.17-1.62.86 2.47 1.93c1.72 1.29 1.93 1.29 1.93 4.19v59.9h.86c.21-.11.54-.33.54-.33V20.19c0-1.72-.21-2.15-.96-2.9 0-.11-1.93-1.61-3.22-2.68z" class="st0"/><path d="M235.01 65.92v-29.1c0-1.5-.53-2.68-2.04-3.54l-13.85-8.26-22.44 13.09v3.12l4.62-2.68V67c0 2.57.64 3.54 2.25 4.51l13.63 8.05 22.54-13.2-.97-2.36-3.74 1.92zm-11.27 4.94-.64.11-8.81-5.16c-1.5-.86-1.83-1.82-1.83-3.76l.11-28.23.64-.22 8.48 4.94c1.71.97 2.04 1.83 2.04 3.65v28.67z" class="st1"/><path d="M198.94 66.99V42.73l-1.07.54-.44.21v24.69c0 2.9 1.29 5.04 3.55 6.33l12.34 7.19 1.4-.75-12.35-7.41c-2.47-1.49-3.43-3.32-3.43-6.54zm21.04-26.52-5.04-3v1.61l2.9 1.61c2.15 1.18 2.15 1.39 2.15 3.65l-.1 22 1.5.86V42.73c-.01-1.29-.44-1.72-1.41-2.26z" class="st0"/><path d="m291.88 70-3.98 2.26-1.39-.86c-1.5-.86-1.83-1.94-1.83-4.51V36.07c0-2.47-.54-3.54-2.04-4.62l-8.27-6.23-12.77 7.3-6.76-7.3-13.53 8.27 1.83 2.14 4.61-2.78 3.33 3.75v42.73h.86c5.37-2.37 7.09-3.12 7.09-3.12 2.58-1.08 3.33-1.93 3.33-4.93V35.63l4.41-2.57 5.15 4.08c1.39 1.18 1.61 2.15 1.61 3.97l.11 29.2c0 3.22.97 5.04 3.11 6.33l4.51 2.69 11.7-6.88-1.08-2.45z" class="st1"/><path d="M271.16 70.32V41.23c0-1.72-.1-1.61-.75-2.15 0 0-2.25-1.83-3.76-3.01l-1.61.87 3.11 2.36c1.72 1.29 1.5 1.39 1.5 3.97V71.5c0 3.86 1.61 6.55 3.86 7.84l3.86 2.15 1.39-.75-3.22-1.93c-2.87-1.73-4.38-4.41-4.38-8.49zm-25.55-33.38 1.61 1.82v42.73h.87c.21-.11.53-.22.53-.22h.11V37.58l-1.39-1.61-1.73.97zm72.12 29.08 1.5.97V32.96l-1.5.97zm-20.08 1.07V44.01l-1.5.75v22.86c0 3.65 1.18 5.26 3 6.44l12.02 7.62 1.4-.86-11.6-7.3c-2.78-1.69-3.32-3.31-3.32-6.43z" class="st0"/><path d="M332.65 66.02V20.51c0-6.65-3-10.95-7.94-13.95l-4.83-3.01-15.14 8.8 3 1.4 4.94-2.68 3.21 1.82c3.44 1.93 5.69 5.8 5.69 9.77v1.71L295.61 39.4v2.9l4.4-2.36v27.27c0 2.36.64 3.33 2.15 4.29l12.88 8.05 22.44-13.1-.96-2.47-3.87 2.04zm-11.06 4.84-.64.11-7.62-4.95c-1.5-.96-2.04-1.72-2.04-3.64V35l9.55-5.8.75.43v41.23z" class="st1"/><path d="m360.56 38.54.1 2.79 1.93 2.37 1.61-.97z" class="st0"/><path d="m367.32 71.5-7.95-5.48c-1.08-.75-1.18-1.28-1.18-2.68v-9.66l21.04-12.77-14.49-15.89-22.43 13.09v3l4.62-2.57v29.74c0 1.71.64 2.79 1.72 3.54l11.92 7.73 16.85-9.77-1.28-3.01-8.82 4.73zm-9.13-37.9.97-.54 8.69 10.2-9.66 6.01V33.6z" class="st1"/><path d="m317.73 23.83 1.5-.86v-.32c0-3.01-1.82-6.12-4.62-7.73-1.07-.65-2.03-1.18-2.03-1.18l-1.29.86.75.42c3.64 2.05 5.69 4.63 5.69 8.81zm26.95 44.45V42.62l-1.07.65-.43.21V68.7c0 2.79 1.08 4.73 2.9 5.91l10.74 7.08 1.5-.86-10.84-7.09c-1.29-.84-2.8-2.45-2.8-5.46z" class="st0"/></svg>',
        ),
        ArchiveCollection(
            name="cnews",
            url="https://cnews.fr",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=CNewsFrontPage,
            logo_background_color="#fff",
            logo_src="https://static.cnews.fr/sites/all/themes/cnewsv2/cnews-logo.svg",
        ),
        ArchiveCollection(
            name="bfmtv",
            url="https://bfmtv.com",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=BfmTvFrontPage,
            logo_background_color="#0101a2",
            logo_src="https://www.bfmtv.com/assets/v5/images/BFMTV-header.030eba2d277d5b5fc0df00daebd9ff70.svg",
        ),
        ArchiveCollection(
            name="le_parisien",
            url="https://www.leparisien.fr/",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=LeParisienFrontPage,
            logo_background_color="#fff",
            logo_content="""
            <svg viewBox="0 0 128 40"><g fill="none" fill-rule="evenodd"><polygon fill="#FFF" fill-rule="nonzero" points="128 0 0 0 0 40 128 40"></polygon><polygon fill="#1EA0E6" fill-rule="nonzero" points="128 0 0 0 0 37 128 37"></polygon><polygon fill="#F03333" fill-rule="nonzero" points="128 38 0 38 0 40 128 40"></polygon><path fill="#FFF" d="M49,15 C49,23 41.5,25.9 40,26.3 L40,36 L36,36 L36,6 L39.3,6 C44.1,6 49,8.2 49,15 Z M44.5,15 C44.5,10.5 42,9.4 40,9.4 L40,22.5 C40.5,22.4 44.5,20.4 44.5,15 Z M14,14 L14,36 L23,36 L23,33 L18,33 L18,14 L14,14 Z M28.2,36.0999 C28.8,36.0999 29,35.9999 29,35.9999 L29.1,35.9999 L29.1,33.1999 L28.6,33.1999 C27.3,33.1999 26,32.1999 25.8,29.6999 C27.5,29.5999 32,27.7999 32,23.4999 C32,19.8999 29.1,18.3999 27.2,18.3999 C25.2,18.3999 22,19.6999 22,27.2999 C22,34.5999 25.6,36.0999 28.2,36.0999 Z M28.5,23.1999 C28.5,25.4999 26.7,26.8999 25.5,26.9999 C25.5,22.0999 26.3,20.9999 27.3,20.9999 C28,20.9999 28.5,21.6999 28.5,23.1999 Z M54.5,35.9999 L58,35.9999 L58,21.5999 C58,17.1999 55.7,15.8999 52.5,15.8999 C50.6,15.8999 49.5,16.4999 49.5,16.4999 L49.5,19.4999 C49.7827,19.4371 50.026,19.3644 50.2607,19.2942 L50.2608,19.2942 C50.7734,19.141 51.2456,18.9999 52,18.9999 C53.1,18.9999 54,19.2999 54,20.4999 L54,20.9999 C52.5,21.1999 47,23.2999 47,29.4999 C47,33.2999 49.9,36.5999 53,36.0999 L54.5,34.6999 L54.5,35.9999 Z M51,29.4999 C51,25.7999 53.5,24.0999 54,23.9999 L54,31.7999 C54,32.1999 53.3,32.9999 52.7,32.9999 C52,32.9999 51,31.8999 51,29.4999 Z M67.5,19.5 C65.5,19.5 64,21.1 64,23.5 L64,36 L60,36 L60,16 L64,16 L64,17.5 C64.5,17 65.5,16 67.5,16 L68,16 L68,19.5 L67.5,19.5 Z M69,10 L69,14 L73,14 L73,10 L69,10 Z M73,16 L73,36 L69,36 L69,16 L73,16 Z M83.9998,30.1999 C83.9998,33.5999 80.9998,36.0999 77.4998,36.0999 C75.9998,36.0999 74.7998,35.8999 73.7998,35.4999 L75.2998,32.4999 C75.8998,32.7999 76.4998,32.8999 77.1998,32.8999 C78.4998,32.8999 79.5998,31.9999 79.5998,30.7999 C79.5998,29.3999 78.9998,28.3999 77.4998,26.6999 C74.8998,24.1999 74.0998,22.8999 74.0998,20.7999 C74.0998,17.9999 76.5998,15.8999 79.8998,15.8999 C81.3998,15.8999 82.2998,15.9999 83.0998,16.2999 L81.5998,19.2999 C81.0998,19.0999 80.6998,18.9999 79.9998,18.9999 C79.0998,18.9999 78.2998,19.6999 78.2998,20.4999 C78.2998,21.2999 78.5998,21.9999 80.2998,23.5999 C82.8998,25.7999 83.9998,27.3999 83.9998,30.1999 Z M85,10 L85,14 L89,14 L89,10 L85,10 Z M85,16 L89,16 L89,36 L85,36 L85,16 Z M101,21.4999 C101,26.4999 96.2,28.7999 94.3,28.9999 C94.5,31.8999 95.9,32.9999 97.3,32.9999 L98,32.9999 L98,35.9999 C98,35.9999 97.6,36.0999 96.9,36.0999 C93.9,36.0999 90,34.4999 90,25.9999 C90,17.1999 93.6,15.8999 96,15.8999 C98.2,15.8999 101,17.2999 101,21.4999 Z M93.9,25.9999 C95.2,25.8999 97.1,24.1999 97.1,21.4999 C97.1,19.6999 96.6,18.9999 95.8,18.9999 C94.8,18.9999 93.9,19.5999 93.9,25.9999 Z M114,22.7997 C114,17.4997 111.1,15.5997 107,15.9997 L106,16.9997 L106,15.9997 L102,15.9997 L102,35.9997 L106,35.9997 L106,21.4997 C106,20.0997 107,18.9997 108,18.9997 C109,18.9997 110,20.0997 110,21.4997 L110,35.9997 L114,35.9997 L114,22.7997 Z"></path></g></svg>
            """,
        ),
        ArchiveCollection(
            name="le_figaro",
            url="https://www.lefigaro.fr/",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=LeFigaroFrontPage,
            logo_background_color="#fff",
            logo_content="""
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 310.3 41.5" style="enable-background:new 0 0 310.3 41.5;" xml:space="preserve"><style type="text/css">	.st0{fill-rule:evenodd;clip-rule:evenodd;fill:#163860;}	.st1{fill-rule:evenodd;clip-rule:evenodd;fill:#4A90E2;}</style><path class="st0" d="M0,8.3h20.8v7h-2.5c-1.3,0-1.6,0.5-1.6,1.7v16c0,0.8,0.7,1.5,1.5,1.5c0,0,0.1,0,0.1,0h6  c0.9,0.1,1.7-0.7,1.8-1.6c0,0,0-0.1,0-0.1V27h8.3v14.4H0v-7h2.4c1.1,0,1.7-0.4,1.7-1.5V17c0-1-0.1-1.6-1.5-1.6H0V8.3L0,8.3z M38,8.3  h34.3V19h-8.6v-1.7c0-1.1-0.5-1.9-2.2-1.9H54v6h8.1v6.4h-8v6.7h7.8c0.9,0.1,1.7-0.6,1.8-1.6c0-0.1,0-0.2,0-0.3v-1.7h8.6v10.6H38v-7  h2c1,0,1.6-0.4,1.6-1.4V17c0-1-0.1-1.7-1.5-1.7h-2L38,8.3L38,8.3z M89.3,8.3h35V19h-8.5v-1.7c0.1-0.9-0.6-1.7-1.6-1.8  c-0.1,0-0.2,0-0.3,0h-7.8v6h7.2v6.3h-7.2v4.8c0,1.4,0.6,1.9,2.3,1.9h2.7v7H89.3v-7h2.9c0.7,0.1,1.3-0.5,1.4-1.2c0-0.1,0-0.1,0-0.2  V17c0-1-0.1-1.7-1.5-1.7h-2.8V8.3z M144.2,17c0-1.2,0.4-1.6,1.6-1.6h2.6v-7h-20.7v7h2.6c1.4,0,1.6,0.6,1.6,1.6v16  c0,1.2-0.7,1.5-1.6,1.5h-2.6v7h20.7v-7h-2.5c-1,0-1.7-0.4-1.7-1.5L144.2,17L144.2,17z M178.9,8.3h7.3V20h-7.4  c-1.5-3.1-4.6-5.1-8-5.1c-4.5,0-8,3.2-8,9.2c0,10,5.6,11,8,11c5,0,6.1-3.6,6.1-5h-4.6V24h15.9l-0.1,4.2c0,0.9-0.9,13.2-18.7,13.2  c-12.8,0-19.4-6.7-19.4-17.2c0-7,5.5-15.9,18.5-15.9c7.3,0,10.4,2.5,10.4,2.5V8.3z M227,34.4c-1.5,0-1.9-1.3-2.7-3.3l-8.8-22.8  h-12.7l-9,24.5c-0.4,1-1.5,1.7-2.6,1.6h-1.8v7H205v-6.7h-2.2c-1,0-1.1-0.7-0.8-1.7l1-3h9.4l1,3.2c0.4,1.1-0.8,1.5-1.5,1.5H210v6.7  h18.7v-7H227z M204.5,25.5l3.2-9.7h0.1l3.2,9.7H204.5z M271,34.4c-1.3,0-1.5-0.6-2.1-1.5c-0.7-0.8-4.6-7-4.6-7s5.8-1.6,5.8-7.8  s-5.2-8.3-7.4-9c-2.2-0.5-7-0.8-8.2-0.8h-22.6v7h2.2c1.4,0,1.6,0.8,1.6,1.7v15.7c0,0.7-0.1,1.7-1.6,1.7h-2.2v7h19.9v-7h-2  c-1.4,0-1.6-0.8-1.6-1.6v-5.3h4.5l8,14h12.6v-7.1C273.3,34.4,271,34.4,271,34.4z M252.7,21.7h-4.5V15h5c1.3,0,3.9,0.5,3.9,3.5  C257.1,20.7,255.4,21.8,252.7,21.7L252.7,21.7z M291.5,8.3c-13.8,0-18.7,8.8-18.7,16.3c0,9.8,7,16.8,18.7,16.8  c10.6,0,18.8-5.2,18.8-16.4C310.3,14.3,302.3,8.3,291.5,8.3z M292,35c-3,0-6.3-1.8-6.3-11c0-5.7,2.2-9.2,6-9.2c3.5,0,6,2.4,6,9.8  C297.7,32.7,295.1,35,292,35z"/><path class="st1" d="M114,32.3c3.2,2.7,6.1,5.8,8.5,9.2l-1.3-1c-3.3-3.6-3.5-3.5-6.3-6c-1.8-1.6-3.8-3-6-4.1l-2.8-1.2v-1.5h3.4  C110.7,29.1,112.4,30.8,114,32.3L114,32.3z M92.5,8.3c6.4,2.7,9,9,9,9v10.4c0,0-5.2-1.1-11.8-5.6l3.1,0.2c0,0-7.2-3.7-9.4-6.3  c1,0.4,2,0.6,3,0.8c0,0-5.4-2.9-7.3-10.8c0.4,0.6,1,1,1.6,1.3c-0.8-2.4-1.2-4.8-1.3-7.3c0,0,6,6.9,13,9C92.6,9,92.4,8.3,92.5,8.3  L92.5,8.3z"/></svg>
            """,
        ),
        ArchiveCollection(
            name="tf1_info",
            url="https://www.tf1info.fr/",
            tz=ZoneInfo("Europe/Paris"),
            FrontPageClass=Tf1InfoFrontPage,
            logo_background_color="#313b7f",
            logo_content="""
            <svg id="prefix__Calque_1" x="0" y="0" viewBox="0 0 1024 314"><linearGradient id="prefix__SVGID_1_" gradientUnits="userSpaceOnUse" x1="82" y1="157" x2="492.4" y2="157"><stop offset="0" stop-color="#172aef"></stop><stop offset="0.445" stop-color="#450588"></stop><stop offset="0.534" stop-color="#730262"></stop><stop offset="1" stop-color="#db0100"></stop></linearGradient><path d="M82 232.2V81.8h410.4v150.4H82z" fill="url(#prefix__SVGID_1_)"></path><radialGradient id="prefix__SVGID_00000176034155888975786460000000547924562293415564_" cx="287.2" cy="190.87" r="209.714" gradientTransform="matrix(1 0 0 -1.023 0 324.21)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0.2"></stop><stop offset="1" stop-opacity="0.2"></stop></radialGradient><path d="M288.6 133.5C186 145.1 82 176.1 82 176.1V81.8h410.4v38.3s-63.2-2.4-203.8 13.4z" fill="url(#prefix__SVGID_00000176034155888975786460000000547924562293415564_)"></path><path id="prefix__Lettering" d="M205.5 104v35.9h-23.8V208h-45.5v-68.1h-23.8V104h93.1zm56.5 0v104h45.2v-32.7H335v-26h-27.8V130H346v-26h-84zm138.5 13.3V208h47V104l-47 13.3z" fill="#fff"></path><path d="M697 104v104h-24.5l-46.4-55.4V208H597V104h24.5l46.4 55.4V104H697zm117 22.7V104h-82v104h29.6v-35.7h31.7v-22.7h-31.7v-22.9H814zm40.2 76.3c18.7 9.3 40.8 9.3 59.5 0 26-13.5 36.1-45.5 22.6-71.5-5-9.7-12.9-17.6-22.6-22.6-18.7-9.3-40.8-9.3-59.5 0-26 13.5-36.1 45.5-22.6 71.5 5.1 9.7 13 17.6 22.6 22.6m44.1-21c-8.9 4.9-19.7 4.9-28.6 0-4.3-2.5-7.8-6.1-10.1-10.5-5-9.7-5-21.3 0-31 2.3-4.4 5.8-8 10.1-10.5 8.9-4.9 19.7-4.9 28.6 0 4.3 2.5 7.8 6.1 10.1 10.5 5 9.7 5 21.3 0 31-2.3 4.4-5.8 8-10.1 10.5m-366.2-78l-.1 104h30V104h-29.9z" fill="#fff"></path></svg>
            """,
        ),
    ]
}
