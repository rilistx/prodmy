from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.database.querys import deactivate_vacancy, get_vacancy_one, create_complaint, get_complaint_count, \
    delete_vacancy
from core.handlers.menu import redirector
from core.keyboards.menu import MenuCallBack
from core.keyboards.admin import get_admin_vacancy_button
from core.schedulers.vacancy import scheduler_deactivate_vacancy
from core.utils.message import get_text_vacancy_method, get_text_vacancy_complaint
from core.utils.settings import complaint_limit


async def method_vacancy_show(
        *,
        callback: CallbackQuery,
        callback_data: MenuCallBack,
        session: AsyncSession,
        apscheduler: AsyncIOScheduler,
):
    text = await get_text_vacancy_method(
        lang=callback_data.lang,
        func_name='show',
        method=callback_data.method,
    )

    await callback.answer(
        text=text,
    )

    await deactivate_vacancy(
        session=session,
        vacancy_id=callback_data.vacancy_id,
        method=callback_data.method,
    )

    if apscheduler.get_job(f'deactivate_vacancy_{str(callback_data.vacancy_id)}'):
        apscheduler.remove_job(f'deactivate_vacancy_{str(callback_data.vacancy_id)}')

    if callback_data.method == 'activate':
        apscheduler.add_job(
            scheduler_deactivate_vacancy,
            id=f'deactivate_vacancy_{str(callback_data.vacancy_id)}',
            trigger='date',
            next_run_time=datetime.now() + timedelta(days=30),
            kwargs={
                'lang': callback_data.lang,
                'chat_id': callback.message.chat.id,
                'vacancy_id': callback_data.vacancy_id,
            },
        )

    return await redirector(
        callback=callback,
        callback_data=callback_data,
        session=session,
        view=callback_data.view,
        level=4,
        key='description',
        page=callback_data.page,
        catalog_id=callback_data.catalog_id,
        subcatalog_id=callback_data.subcatalog_id,
        vacancy_id=callback_data.vacancy_id,
    )


async def method_vacancy_complaint(
        *,
        bot: Bot,
        callback: CallbackQuery,
        callback_data: MenuCallBack,
        session: AsyncSession,
):
    vacancy = await get_vacancy_one(
        session=session,
        vacancy_id=callback_data.vacancy_id,
    )

    if vacancy:
        await create_complaint(
            session=session,
            user_id=callback.from_user.id,
            vacancy_id=callback_data.vacancy_id,
        )

        text = await get_text_vacancy_method(
            lang=callback_data.lang,
            func_name='complaint',
        )

        await callback.answer(
            text=text,
        )

    complaint_count = await get_complaint_count(
        session=session,
        vacancy_id=callback_data.vacancy_id,
    )

    if complaint_count.complaint_count == complaint_limit:
        text = await get_text_vacancy_complaint(
            lang=callback_data.lang,
        )
        reply_markup = get_admin_vacancy_button(
            lang=callback_data.lang,
            vacancy_id=callback_data.vacancy_id,
        )

        await bot.send_message(
            chat_id=vacancy.user_id,
            text=text,
            reply_markup=reply_markup,
        )

    return await redirector(
        callback=callback,
        callback_data=callback_data,
        session=session,
        view=callback_data.view,
        level=3 if complaint_count.complaint_count == complaint_limit else 4,
        key='view' if complaint_count.complaint_count == complaint_limit else 'description',
        page=callback_data.page - 1 if callback_data.page - 1 != 0 else callback_data.page,
        catalog_id=callback_data.catalog_id,
        subcatalog_id=callback_data.subcatalog_id,
    )


async def method_vacancy_delete(
        *,
        callback: CallbackQuery,
        callback_data: MenuCallBack,
        session: AsyncSession,
        apscheduler: AsyncIOScheduler,
):
    if apscheduler.get_job(f'deactivate_vacancy_{str(callback_data.vacancy_id)}'):
        apscheduler.remove_job(f'deactivate_vacancy_{str(callback_data.vacancy_id)}')

    await delete_vacancy(
        session=session,
        vacancy_id=callback_data.vacancy_id,
    )

    text = await get_text_vacancy_method(
        lang=callback_data.lang,
        func_name='delete',
    )

    await callback.answer(
        text=text,
    )

    return await redirector(
        callback=callback,
        callback_data=callback_data,
        session=session,
        view=callback_data.view,
        level=3,
        key='view',
        page=callback_data.page - 1 if callback_data.page - 1 != 0 else 1,
        catalog_id=callback_data.catalog_id,
        subcatalog_id=callback_data.subcatalog_id,
    )


def check_update_vacancy(
        *,
        old_data,
        new_data,
        method: str,
) -> bool:
    if (old_data.name != new_data['name']
            or old_data.description != new_data['description']
            or old_data.requirement != new_data['requirement']
            or old_data.employment != new_data['employment']
            or old_data.experience != new_data['experience']
            or old_data.schedule != new_data['schedule']
            or old_data.remote != new_data['remote']
            or old_data.language != new_data['language']
            or old_data.foreigner != new_data['foreigner']
            or old_data.disability != new_data['disability']
            or old_data.salary != new_data['salary']
            or old_data.catalog_id != new_data['catalog_id']
            or (old_data.subcatalog_id != new_data['subcatalog_id'] and method != "channel")
            or old_data.currency_id != new_data['currency_id']
            or old_data.country_id != new_data['country_id']
            or old_data.region_id != new_data['region_id']
            or old_data.city_id != new_data['city_id']):
        return True
    return False
