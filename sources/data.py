import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import click
import click.testing
import pandas as pd


class AbstractFileHandler:
    """Abstract definition for a file reader and writer"""

    _mime = None

    def __init__(
        self, filepath: None | str | Path = None, data: Any = None, uuid: bool = False
    ):
        # create attributes
        if filepath is not None:
            self.filepath = Path(filepath)
        else:
            self.filepath = None
        self.uuid = uuid
        self._mime = None
        if data:
            self._raw = data
        else:
            self._raw: dict | None = None
        self._meta: dict | None = None
        self._data: list | None = None

        # populate attributes
        if filepath:
            self._raw = self.raw()
        elif data:
            self._raw = data
        else:
            raise ValueError(
                f"Missing filepath or raw data for class {self.__class__.__name__} instanciation"
            )
        self._meta = self.meta()
        self._data = self.read()

    @classmethod
    def from_file(cls, filepath: str | Path, uuid: bool = False):
        return cls(filepath=filepath, uuid=uuid)

    @classmethod
    def from_obj(cls, obj):
        """create a file handler straight from the raw instance data"""
        return cls(data=obj)

    def raw(self) -> Any:
        """return the raw data. This method is in charge for reading the contents of the mime type"""
        raise NotImplementedError

    def read(self) -> Any:
        """return the file data"""
        if self._data:
            return self._data
        else:
            return self._raw.get("data")  # type: ignore

    def meta(self):
        """return the file meta"""
        if self._meta:
            return self._meta
        else:
            return {key: value for key, value in self._raw.items() if key != "data"}  # type: ignore

    def write(self) -> None:
        """write the data to file"""
        raise NotImplementedError

    def auto_name(
        self,
        fdir: str = ".",
        topic: str | None = None,
        args: list[str] = [],
        stamp: str | None = None,
        from_meta: bool = False,
        uuid: bool = False,
        overwrite: bool = False,
        name_sep: str = "_",
    ) -> str:
        """use the file meta to suggest an automatic name or make new uuid, no guarantee of unicity or file safety"""

        if from_meta:
            assert self._meta, "No metadata associated to the file"
            _stamp: str = (
                stamp
                or self._meta.get("timestamp")
                or datetime.now().isoformat(timespec="miliseconds")
            )
            _topic: str = topic or self._meta.get("script") or "noscript"
            _args: str = name_sep.join(args) or name_sep.join(
                self._meta.get("args", [])
            )
            res = str(
                Path(fdir).absolute()
                / f"{_stamp}_{_topic}_{_args}.{self.__class__._mime}"
            )
        elif uuid:
            return str(Path(fdir).absolute() / f"{str(uuid4())}.{self.__class__._mime}")
        else:  # make new file from old file name
            assert self._meta, "No metadata associated to the file"
            suffixes = ".".join(self.filepath.suffixes)  # type: ignore
            new_suffixes = ".".join(
                [f".{self.__class__._mime}", *self.filepath.suffixes[1:]]
            )  # type: ignore
            res = str(
                Path(fdir).absolute()
                / f"{str(self.filepath)[:-len(suffixes)]}{new_suffixes}"
            )

        if overwrite:
            return res
        else:
            suffixes = ".".join(Path(res).suffixes)  # type: ignore
            file_template = "{name}{num}{ext}"
            name = str(self.filepath)[: -len(suffixes) - 1]
            glob = file_template.format(name=name, num="*", ext=suffixes)
            nums = len(list(Path(res).parent.glob(glob)))
            if nums < 1:
                index = ""
            else:
                index = f" {nums}"
            return str(
                Path(fdir).absolute()
                / file_template.format(name=name, num=index, ext=suffixes)
            )


class StdOutFileHandler(AbstractFileHandler): ...


class CSVFileHandler(AbstractFileHandler):
    _mime = "csv"

    # def __init__(
    #     self, filepath: None | str | Path = None, data: Any = None, uuid: bool = False
    # ):
    #     super().__init__(filepath, uuid)
    #     self._mime = "csv"

    def raw(self, cache: bool = True, **kwargs) -> Any:
        if cache and self._raw is not None:
            return self._raw
        else:
            meta = guess_meta(self.filepath)  # type: ignore
            data = pd.read_csv(self.filepath, **kwargs).to_json(orient="records")  # type: ignore
            return {**meta, "data": data}

    def write(
        self,
        data: str | bytes | None = None,
        fname: str | Path | None = None,
        fdir: str = ".",
        topic: str | None = None,
        args: list[str] = [],
        stamp: str | None = None,
        from_meta: bool = False,
        uuid: bool = False,
        overwrite: bool = False,
        name_sep: str = "_",
        **kwargs,
    ) -> None:
        """write the data to file"""
        if fname:
            fpth = fname
        else:
            fpth = self.auto_name(
                fdir=fdir,
                topic=topic,
                args=args,
                stamp=stamp,
                from_meta=from_meta,
                uuid=uuid,
                overwrite=overwrite,
                name_sep=name_sep,
            )

        if data:
            pd.DataFrame(data).to_csv(fpth, **kwargs)
        else:
            pd.DataFrame(self.read()).to_csv(fpth, **kwargs)


class JSONFileHandler(AbstractFileHandler):
    _mime = "json"
    # def __init__(
    #     self, filepath: None | str | Path = None, data: Any = None, uuid: bool = False
    # ):
    #     super().__init__(filepath, uuid)
    #     self._mime = "json"

    def raw(self, cache: bool = True, **kwargs):
        if cache and self._raw is not None:
            return self._raw
        else:
            return json.loads(self.filepath.read_bytes(), **kwargs)  # type: ignore

    def write(
        self,
        data: str | bytes | None = None,
        fname: str | Path | None = None,
        fdir: str | None = None,
        topic: str | None = None,
        stamp: str | None = None,
        uuid: bool = False,
    ) -> None:
        """write the data to file"""
        if fname:
            fpth = fname
        else:
            fpth = self.auto_name(topic=topic, stamp=stamp, uuid=uuid)
            if fdir:
                fpth = Path(fdir) / fpth
        with open(fpth, "w") as f:
            if data:
                f.write(json.dumps(data, indent=2, default=str))
            else:
                f.write(json.dumps(self.raw, indent=2, default=str))


mimes = {
    "out": StdOutFileHandler,
    "json": JSONFileHandler,
    "csv": CSVFileHandler,
}


def guess_mime(filename: str | Path):
    """utility function returns the file handler class associated with its file mime type. Naive implementation. Does not handle file compression."""
    fname = str(filename)
    for ext in mimes:
        if fname.endswith(ext):
            return mimes[ext]
    raise ValueError(f"Unable to find suitable mime-type for file: {fname}")  # Catch Me


def guess_meta(
    filename: str | Path,
    topic: str | None = None,
    stamp: str | None = None,
    script_version: str | None = None,
    url: str | None = None,
    sep: str = "_",
) -> dict:
    """utility function that attempts to extract the file metadata from the filename"""
    _topic = ""
    _stamp = ""
    _script_version = ""
    _url = ""

    if filename:
        f, _ = str(filename).split(".")
        _stamp, *tmp = f.split(sep)
        _topic = sep.join(tmp)

    _topic = str(_topic or topic)
    _script_version = str(_script_version or script_version)
    _url = str(_url or url)
    _stamp = str(_stamp or stamp)

    return {
        "topic": _topic,
        "script_version": _script_version,
        "url": _url,
        "timestamp": _stamp,
    }


@click.group(name="data", help="Scraped data management and conversion commands")
def cli():
    pass


@click.command()
def to_df(): ...


@click.command()
@click.argument("filenames", type=click.Path(exists=True), nargs=-1)
def to_csv(filenames):
    """Transform a scraped file to csv format"""
    for filename in filenames:
        # read
        read_handler = guess_mime(filename)(filepath=filename)

        # write
        write_handler = CSVFileHandler.from_obj(read_handler.raw())
        write_handler.filepath = read_handler.filepath
        write_handler.write()


@click.command()
def to_arrow(): ...


@click.command()
def to_excel(): ...


@click.command()
def to_parquet(): ...


# data.add_command(to_df)
cli.add_command(to_csv)
# data.add_command(to_arrow)
# data.add_command(to_excel)

if __name__ == "__main__":
    runner = click.testing.CliRunner()
    result = runner.invoke(to_csv, args=["20241125_gdpr.json"])
    assert result.exit_code == 0
