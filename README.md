# neokuro

Generate [mokuro](https://github.com/kha-white/mokuro) files using [owocr](https://github.com/AuroraWright/owocr) as the OCR backend.

## Install Instructions

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (should theoretically work with python3-pip as well) and then run:

```
uv tool install git+https://github.com/kamperemu/neokuro
```

## Usage Instructions

Install and open owocr with read_from = websocket, write_to = websocket, output_format = json (cli argument or config file/editor) and keep it open in the background.

If you're running owocr through cli you can run:

```
owocr -r websocket -w websocket -of json
```

If your directory structure looks somewhat like this:

```
manga/
├─vol1/
├─vol2/
├─vol3/
└─vol4/
```

You can process one volume by running:

```
neokuro /path/to/manga/vol1
```

You can process all volumes by running:

```
neokuro --parent_dir /path/to/manga
```

This will generate mokuro files for each volume in the /path/to/manga folder which can be used with [mokuro reader](https://reader.mokuro.app).

## Resuming interrupted runs

OCR processing a large amount of volumes can take a long time. If you're worried about the process being interrupted, you can pass the `--save_ocr` flag:

```
neokuro --parent_dir /path/to/manga --save_ocr
```

This saves the OCR data of every processed page to a temporary `_ocr` folder (created next to the volumes). On subsequent runs with the same flag, pages that already have cached OCR data are skipped and only the remaining pages are processed, so no work is lost. The `_ocr` folder can be safely deleted once all mokuro files have been generated.

## Supported Formats

Volumes via single or batch processing methods can be one of the following formats:

- Directory of images
- CBZ file
- ZIP file

All formats should contain the images to be processed at the top level of the volume, as any nested folders will be skipped.

Good examples:

```
vol1/
├─image_001.jpg
├─image_002.jpg
└─image_003.jpg
```

```
vol1.cbz
├─image_001.jpg
├─image_002.jpg
└─image_003.jpg
```

Bad examples:

```
vol1/
├─nested_folder/
│ └─image_001.jpg
├─image_001.jpg
├─image_002.jpg
└─image_003.jpg
```

```
vol1.cbz
└─nested_folder/
  ├─image_001.jpg
  ├─image_002.jpg
  └─image_003.jpg
```
