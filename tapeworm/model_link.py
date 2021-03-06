from collections import namedtuple
from google.cloud import datastore

Link = namedtuple("Link", ["id", "link", "title", "by", "by_username", "date"])


class Links:
    def __init__(self, ds):
        self.client = ds

    def from_datastore(self, entity):
        if not entity:
            return None
        if isinstance(entity, list):
            entity = entity.pop()

        by_username = entity["by"]
        if "by_username" in entity:
            by_username = entity["by_username"]

        return Link(
            id=entity.key.id,
            link=entity["link"],
            title=entity["title"],
            by=entity["by"],
            by_username=by_username,
            date=entity["date"],
        )

    @staticmethod
    def from_dict(data):
        """
        Creates a Link from a dictionary. The output from this function
        can be passed into create with Link._asdict()
        """
        if not isinstance(data, dict):
            raise ValueError("data must be type of dict")
        if not data:
            raise ValueError("data must be valid")

        return Link(
            id=None,
            link=data["link"],
            title=data["title"],
            by=data["by"],
            by_username=data["by_username"],
            date=data["date"],
        )

    def create_multi(self, datas):
        if not isinstance(datas, list):
            raise ValueError("datas must be type of List containing Link")

        with self.client.batch() as batch:
            for data in datas:
                entity = datastore.Entity(key=self.client.key("Link"))
                as_dict = data._asdict()
                _ = as_dict.pop("id")

                entity.update(as_dict)
                batch.put(entity)
                yield self.from_datastore(entity)

    def list_links(self, offset=0, limit=10):
        query = self.client.query(kind="Link", order=["-date"])
        query_iterator = query.fetch(limit=limit, offset=offset)
        page = next(query_iterator.pages)

        entities = list(map(self.from_datastore, page))
        return entities

    def read(self, identifier):
        if not identifier:
            raise ValueError("id is not valid")
        key = self.client.key("Link", int(identifier))
        return self.from_datastore(self.client.get(key))
