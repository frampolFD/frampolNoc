from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Branch, City, Customer, ISP, Suburb, User, WANLink
from app.schemas import (
    BranchIn,
    BranchOut,
    CityIn,
    CityOut,
    CustomerIn,
    CustomerOut,
    ISPIn,
    ISPOut,
    SuburbIn,
    SuburbOut,
)

router = APIRouter(prefix="/api", tags=["inventory"], dependencies=[Depends(get_current_user)])


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.name).all()


@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/cities", response_model=list[CityOut])
def list_cities(customer_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(City)
    if customer_id is not None:
        query = query.filter(City.customer_id == customer_id)
    return query.order_by(City.name).all()


@router.post("/cities", response_model=CityOut)
def create_city(payload: CityIn, db: Session = Depends(get_db)):
    if not db.get(Customer, payload.customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    city = City(**payload.model_dump())
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


@router.get("/suburbs", response_model=list[SuburbOut])
def list_suburbs(city_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Suburb)
    if city_id is not None:
        query = query.filter(Suburb.city_id == city_id)
    return query.order_by(Suburb.name).all()


@router.post("/suburbs", response_model=SuburbOut)
def create_suburb(payload: SuburbIn, db: Session = Depends(get_db)):
    if not db.get(City, payload.city_id):
        raise HTTPException(status_code=404, detail="City not found")
    suburb = Suburb(**payload.model_dump())
    db.add(suburb)
    db.commit()
    db.refresh(suburb)
    return suburb


@router.get("/branches", response_model=list[BranchOut])
def list_branches(
    customer_id: int | None = None,
    city_id: int | None = None,
    suburb_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Branch)
    if customer_id is not None:
        query = query.filter(Branch.customer_id == customer_id)
    if city_id is not None:
        query = query.filter(Branch.city_id == city_id)
    if suburb_id is not None:
        query = query.filter(Branch.suburb_id == suburb_id)
    return query.order_by(Branch.name).all()


@router.get("/branches/{branch_id}/breadcrumb")
def branch_breadcrumb(branch_id: int, db: Session = Depends(get_db)):
    branch = db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return {
        "customer": branch.customer.name,
        "city": branch.city.name,
        "suburb": branch.suburb.name if branch.suburb else None,
        "branch": branch.name,
        "branch_id": branch.id,
    }


@router.post("/branches", response_model=BranchOut)
def create_branch(payload: BranchIn, db: Session = Depends(get_db)):
    if not db.get(Customer, payload.customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")

    city = db.get(City, payload.city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    if city.customer_id != payload.customer_id:
        raise HTTPException(status_code=422, detail="City does not belong to the supplied customer")

    if payload.suburb_id:
        suburb = db.get(Suburb, payload.suburb_id)
        if not suburb:
            raise HTTPException(status_code=404, detail="Suburb not found")
        if suburb.city_id != payload.city_id:
            raise HTTPException(status_code=422, detail="Suburb does not belong to the supplied city")

    branch = Branch(**payload.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/isps", response_model=list[ISPOut])
def list_isps(db: Session = Depends(get_db)):
    return db.query(ISP).order_by(ISP.name).all()


@router.post("/isps", response_model=ISPOut)
def create_isp(payload: ISPIn, db: Session = Depends(get_db)):
    isp = ISP(**payload.model_dump())
    db.add(isp)
    db.commit()
    db.refresh(isp)
    return isp


@router.get("/explorer")
def explorer_tree(db: Session = Depends(get_db)):
    """Full Customer -> City -> Suburb -> Branch -> WAN Link tree for the
    always-visible Explorer sidebar."""
    customers = (
        db.query(Customer)
        .options(
            selectinload(Customer.cities).selectinload(City.suburbs),
            selectinload(Customer.cities).selectinload(City.branches).selectinload(Branch.wan_links),
        )
        .order_by(Customer.name)
        .all()
    )

    def branch_node(branch: Branch):
        return {
            "id": branch.id,
            "name": branch.name,
            "wan_links": [{"id": w.id, "name": w.name_generated} for w in branch.wan_links],
        }

    tree = []
    for customer in customers:
        city_nodes = []
        for city in customer.cities:
            suburb_nodes = [
                {
                    "id": suburb.id,
                    "name": suburb.name,
                    "branches": [branch_node(b) for b in city.branches if b.suburb_id == suburb.id],
                }
                for suburb in city.suburbs
            ]
            branches_without_suburb = [branch_node(b) for b in city.branches if b.suburb_id is None]
            city_nodes.append(
                {
                    "id": city.id,
                    "name": city.name,
                    "suburbs": suburb_nodes,
                    "branches": branches_without_suburb,
                }
            )
        tree.append({"id": customer.id, "name": customer.name, "cities": city_nodes})

    return tree
