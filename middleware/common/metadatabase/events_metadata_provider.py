from sqlalchemy import and_

from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import Events
from middleware.common.metadatabase.model.difw_metadb_model import SubEvents


class EventsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with events
    """

    def insert_event(self,  event: Events, user_id: str):
        """
        Insert event

        @param event: event which will be created
        @param user_id: user who create the event

        :return: inserted event
        """
        self.logger.info(f"User {user_id} is going to create event:{event.EVENT_ID} ")
        return self.insert_record(event, user_id)

    def insert_or_update_event(self, event: Events, user_id: str):
        """
        Insert or update event.

        @param event: event which will
        @param user_id: user who create/update the event

        :return: inserted or updated event
        """
        return self.insert_or_update_record(event, user_id)

    def update_event(self, event: Events, user_id: str):
        """
        Update event

        @param event: event which will be updated
        @param user_id: user who update the event

        :return: updated event
        """
        self.logger.info(f"User {user_id} is going to update event: {event.EVENT_ID} ")
        return self.update_record(event, user_id)

    def get_event(self, event_id: str = None, user_id: str = None):
        """
        Get specified event details from DB.

        @param event_id:
        @param user_id:
        @return:
        """
        self.logger.info(f"user {user_id} is going to retrieve the event  {event_id} details ")
        return Events(EVENT_ID=event_id).get_unique(self.session)

    def get_sub_events(self, sub_event_id: str = None, user_id: str = None):
        """
        Get specified sub event details from DB.

        @param sub_event_id:
        @param user_id:
        @return:
        """
        self.logger.info(f"User {user_id} is retrieving sub events: {sub_event_id} details ")
        return SubEvents.get_many(self.session, and_(SubEvents.EVENT_ID == sub_event_id))

    def insert_sub_event(self, sub_events: SubEvents, user_id: str):
        """
        creates a sub event in MetaDB for the given event

        @param sub_events
        @param user_id
        """
        self.logger.info(f"User {user_id} is going to create sub event: {sub_events.EVENT_ID} ")
        return self.insert_record(sub_events, user_id)

    def update_sub_event(self, sub_events: SubEvents, user_id: str):
        """
        updates sub event in MetaDB for the given project

        @param sub_events
        @param user_id
        """
        self.logger.info(f"User {user_id} is going to update sub event: {sub_events.EVENT_ID} ")
        return self.update_record(sub_events, user_id)

    def insert_or_update_sub_event(self, sub_event: SubEvents, user_id: str):
        """
        Insert or update sub event.

        @param sub_event: sub event which will be created
        @param user_id: user who create/update the event

        :return: inserted or updated event
        """
        return self.insert_or_update_record(sub_event, user_id)
