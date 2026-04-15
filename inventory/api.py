from flask import Flask, jsonify, request

from .database import initialize_database
from .inventory import (
    add_item,
    check_restock,
    get_instock_rate,
    remove_item,
    run_audit_report,
    update_quantity,
)
from .members import add_member, get_member, get_resolution_rate, resolve_inquiry, update_member


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    initialize_database(db_path)

    @app.post("/items")
    def create_item():
        data = request.get_json(force=True)
        item = add_item(
            name=data["name"],
            sku=data["sku"],
            quantity=int(data.get("quantity", 0)),
            threshold=int(data.get("threshold", 0)),
            db_path=db_path,
        )
        return jsonify(item), 201

    @app.delete("/items/<int:item_id>")
    def delete_item(item_id: int):
        deleted = remove_item(item_id=item_id, db_path=db_path)
        return jsonify({"deleted": deleted}), (200 if deleted else 404)

    @app.patch("/items/<int:item_id>/quantity")
    def patch_item_quantity(item_id: int):
        data = request.get_json(force=True)
        item = update_quantity(item_id=item_id, quantity=int(data["quantity"]), db_path=db_path)
        if item is None:
            return jsonify({"error": "item not found"}), 404
        return jsonify(item), 200

    @app.get("/items/<int:item_id>/restock")
    def get_restock(item_id: int):
        return jsonify(check_restock(item_id=item_id, db_path=db_path)), 200

    @app.get("/items/instock-rate")
    def items_instock_rate():
        return jsonify({"in_stock_rate": get_instock_rate(db_path=db_path)}), 200

    @app.get("/items/audit")
    def items_audit():
        return jsonify(run_audit_report(db_path=db_path)), 200

    @app.post("/members")
    def create_member():
        data = request.get_json(force=True)
        member = add_member(name=data["name"], email=data["email"], db_path=db_path)
        return jsonify(member), 201

    @app.get("/members/<int:member_id>")
    def read_member(member_id: int):
        member = get_member(member_id=member_id, db_path=db_path)
        if member is None:
            return jsonify({"error": "member not found"}), 404
        return jsonify(member), 200

    @app.patch("/members/<int:member_id>")
    def patch_member(member_id: int):
        data = request.get_json(force=True)
        member = update_member(
            member_id=member_id,
            name=data.get("name"),
            email=data.get("email"),
            db_path=db_path,
        )
        if member is None:
            return jsonify({"error": "member not found"}), 404
        return jsonify(member), 200

    @app.post("/members/<int:member_id>/resolve-inquiry")
    def post_resolve_inquiry(member_id: int):
        data = request.get_json(force=True)
        member = resolve_inquiry(
            member_id=member_id,
            resolved=bool(data.get("resolved", False)),
            db_path=db_path,
        )
        if member is None:
            return jsonify({"error": "member not found"}), 404
        return jsonify(member), 200

    @app.get("/members/<int:member_id>/resolution-rate")
    def member_resolution_rate(member_id: int):
        rate = get_resolution_rate(member_id=member_id, db_path=db_path)
        if rate is None:
            return jsonify({"error": "member not found"}), 404
        return jsonify({"resolution_rate": rate}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
