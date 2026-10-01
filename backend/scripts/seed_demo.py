import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.db.session import session_factory
from app.models import (
    Activity,
    AIConfiguration,
    Client,
    ClientAssignment,
    ClientContact,
    Department,
    Organization,
    User,
    UserRole,
    UserStatus,
)
from app.models.activity import ActivityStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.activities import ActivityRequest, LegacyActivityType
from app.schemas.summaries import UpdateAIConfigurationRequest
from app.services.activities import create_activity
from app.services.ai_configuration import update_ai_configuration
from app.services.assignments import assign_client
from app.services.clients import create_client, create_contact


@dataclass(frozen=True)
class ActivitySeed:
    title: str
    description: str
    next_action: str | None
    activity_type: LegacyActivityType
    department: str
    day_offset: int
    status: ActivityStatus


@dataclass(frozen=True)
class ClientSeed:
    name: str
    address: str
    notes: str
    contact_name: str
    contact_position: str
    contact_email: str
    contact_phone: str
    activities: tuple[ActivitySeed, ...]


CLIENTS = (
    ClientSeed(
        name="Atlántico Coworking",
        address="Calle León y Castillo, 42, Las Palmas de Gran Canaria",
        notes="Cliente demo interesado en renovar su identidad y mejorar la comunicación digital.",
        contact_name="Carla Santana",
        contact_position="Directora de operaciones",
        contact_email="carla.santana@example.test",
        contact_phone="+34 600 100 201",
        activities=(
            ActivitySeed(
                "Revisar objetivos de la campaña",
                "Llamada con Carla para concretar públicos, calendario y objetivos de captación.",
                "Preparar una propuesta visual con dos líneas creativas.",
                LegacyActivityType.CALL,
                "comunicación",
                -8,
                ActivityStatus.COMPLETED,
            ),
            ActivitySeed(
                "Validar primeras referencias visuales",
                "Reunión de diseño para revisar tipografías, colores y aplicaciones de marca.",
                "Aplicar los comentarios en la siguiente versión.",
                LegacyActivityType.MEETING,
                "diseño",
                -5,
                ActivityStatus.COMPLETED,
            ),
            ActivitySeed(
                "Enviar resumen de decisiones",
                "Enviar al cliente el resumen de los acuerdos y el calendario actualizado.",
                None,
                LegacyActivityType.EMAIL,
                "comunicación",
                0,
                ActivityStatus.PENDING,
            ),
            ActivitySeed(
                "Preparar propuesta visual",
                "Crear dos propuestas de portada y aplicaciones para redes sociales.",
                None,
                LegacyActivityType.OTHER,
                "diseño",
                4,
                ActivityStatus.PENDING,
            ),
            ActivitySeed(
                "Revisar resultados de lanzamiento",
                "Analizar alcance, respuestas y solicitudes recibidas tras el lanzamiento.",
                None,
                LegacyActivityType.MEETING,
                "comunicación",
                10,
                ActivityStatus.PENDING,
            ),
        ),
    ),
    ClientSeed(
        name="Verde Norte Restauración",
        address="Avenida de Canarias, 18, Santa Cruz de Tenerife",
        notes="Cliente demo con seguimiento técnico y planificación de comunicación mensual.",
        contact_name="Diego Hernández",
        contact_position="Responsable de marketing",
        contact_email="diego.hernandez@example.test",
        contact_phone="+34 600 100 202",
        activities=(
            ActivitySeed(
                "Resolver incidencia del formulario",
                "Se corrigió el error que impedía enviar solicitudes desde dispositivos móviles.",
                "Comprobar durante una semana que no aparezcan nuevos errores.",
                LegacyActivityType.INCIDENT,
                "informática",
                -12,
                ActivityStatus.COMPLETED,
            ),
            ActivitySeed(
                "Planificar campaña de temporada",
                "Reunión para definir promociones, mensajes y canales de la campaña de otoño.",
                "Redactar los primeros mensajes para revisión.",
                LegacyActivityType.MEETING,
                "comunicación",
                -7,
                ActivityStatus.COMPLETED,
            ),
            ActivitySeed(
                "Registrar cambios de carta",
                "Se documentaron las nuevas secciones y fotografías necesarias "
                "para actualizar la web.",
                "Solicitar las fotografías definitivas al cliente.",
                LegacyActivityType.NOTE,
                "diseño",
                -2,
                ActivityStatus.COMPLETED,
            ),
            ActivitySeed(
                "Comprobar formularios y reservas",
                "Revisar el formulario de contacto y el enlace externo de reservas.",
                None,
                LegacyActivityType.CALL,
                "informática",
                0,
                ActivityStatus.PENDING,
            ),
            ActivitySeed(
                "Enviar propuesta de contenidos",
                "Enviar la propuesta mensual de publicaciones y promociones al cliente.",
                None,
                LegacyActivityType.EMAIL,
                "comunicación",
                7,
                ActivityStatus.PENDING,
            ),
        ),
    ),
)


async def seed() -> None:
    settings = get_settings()
    if settings.app_env != "development":
        raise RuntimeError("Demo data can only be created in development")

    async with session_factory() as session:
        organizations = list(await session.scalars(select(Organization)))
        if len(organizations) != 1:
            raise RuntimeError("Demo seed requires exactly one organization")
        organization = organizations[0]
        owner = await session.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.role == UserRole.OWNER,
                User.status == UserStatus.ACTIVE,
            )
        )
        employee = await session.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.role == UserRole.EMPLOYEE,
                User.status == UserStatus.ACTIVE,
            ).order_by(User.full_name)
        )
        if owner is None or employee is None:
            raise RuntimeError("An active owner and employee are required")

        departments = {
            item.normalized_name: item
            for item in await session.scalars(
                select(Department).where(Department.organization_id == organization.id)
            )
        }
        required_departments = {
            activity.department for item in CLIENTS for activity in item.activities
        }
        missing = required_departments - departments.keys()
        if missing:
            raise RuntimeError(f"Missing demo departments: {', '.join(sorted(missing))}")

        authorization = AuthorizationContext(
            user_id=owner.id,
            organization_id=organization.id,
            organization_mode=organization.mode,
            role=owner.role,
            department_ids=frozenset(item.id for item in departments.values()),
        )
        created_clients = 0
        created_activities = 0

        for client_seed in CLIENTS:
            client = await session.scalar(
                select(Client).where(
                    Client.organization_id == organization.id,
                    Client.name == client_seed.name,
                )
            )
            if client is None:
                client = await create_client(
                    session,
                    authorization=authorization,
                    name=client_seed.name,
                    address=client_seed.address,
                    notes=client_seed.notes,
                )
                created_clients += 1

            contact_exists = await session.scalar(
                select(ClientContact.id).where(
                    ClientContact.organization_id == organization.id,
                    ClientContact.client_id == client.id,
                    ClientContact.email == client_seed.contact_email,
                )
            )
            if contact_exists is None:
                await create_contact(
                    session,
                    authorization=authorization,
                    client_id=client.id,
                    full_name=client_seed.contact_name,
                    position=client_seed.contact_position,
                    email=client_seed.contact_email,
                    phone=client_seed.contact_phone,
                    notes="Contacto generado para pruebas locales.",
                )

            assignment_exists = await session.scalar(
                select(ClientAssignment.id).where(
                    ClientAssignment.organization_id == organization.id,
                    ClientAssignment.client_id == client.id,
                    ClientAssignment.user_id == employee.id,
                )
            )
            if assignment_exists is None:
                await assign_client(
                    session,
                    authorization=authorization,
                    client_id=client.id,
                    user_id=employee.id,
                )

            for activity_seed in client_seed.activities:
                activity_exists = await session.scalar(
                    select(Activity.id).where(
                        Activity.organization_id == organization.id,
                        Activity.client_id == client.id,
                        Activity.title == activity_seed.title,
                    )
                )
                if activity_exists is not None:
                    continue
                scheduled_for = date.today() + timedelta(days=activity_seed.day_offset)
                occurred_at = (
                    datetime.now(UTC) + timedelta(days=activity_seed.day_offset)
                    if activity_seed.status is ActivityStatus.COMPLETED
                    else None
                )
                await create_activity(
                    session,
                    authorization=authorization,
                    client_id=client.id,
                    payload=ActivityRequest(
                        type=activity_seed.activity_type,
                        title=activity_seed.title,
                        description=activity_seed.description,
                        next_action=activity_seed.next_action,
                        scheduled_for=scheduled_for,
                        occurred_at=occurred_at,
                        status=activity_seed.status,
                        assigned_to_user_id=employee.id,
                        department_id=departments[activity_seed.department].id,
                    ),
                )
                created_activities += 1

        existing_ai_configuration = await session.get(AIConfiguration, organization.id)
        if existing_ai_configuration is None:
            await update_ai_configuration(
                session,
                authorization=authorization,
                settings=settings,
                payload=UpdateAIConfigurationRequest(
                    provider="ollama",
                    model="llama3.2:1b",
                ),
            )

        await session.commit()
        print(
            f"Demo ready: {created_clients} clients and {created_activities} activities created. "
            "Ollama configured with llama3.2:1b."
        )


if __name__ == "__main__":
    asyncio.run(seed())
